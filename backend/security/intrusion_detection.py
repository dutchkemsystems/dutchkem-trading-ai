"""
V5 Intrusion Detection / Prevention System (IDS/IPS).

Provides pattern-based attack detection, behavioral anomaly detection,
brute-force and credential-stuffing detection, API-abuse detection,
and trade-anomaly detection. All alerts are persisted as SecurityEvent
records with hash-chain integrity.
"""

import logging
import re
import time
from collections import defaultdict
from datetime import timedelta
from threading import Lock
from typing import Any

from django.conf import settings
from django.utils import timezone

from .models import BlockedIP, SecurityEvent, ThreatLevel

logger = logging.getLogger("security.ids")

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _get(name: str, default: Any) -> Any:
    return getattr(settings, name, default)


class _Config:
    # Brute-force thresholds
    BRUTE_FORCE_FAILURES = _get("IDS_BRUTE_FORCE_FAILURES", 5)
    BRUTE_FORCE_WINDOW = _get("IDS_BRUTE_FORCE_WINDOW", 300)  # seconds

    # Credential stuffing
    STUFFING_IP_THRESHOLD = _get("IDS_CREDENTIAL_STUFFING_IP_THRESHOLD", 10)
    STUFFING_WINDOW = _get("IDS_CREDENTIAL_STUFFING_WINDOW", 600)

    # Rate analysis
    RATE_SPIKE_MULTIPLIER = _get("IDS_RATE_SPIKE_MULTIPLIER", 3.0)
    RATE_WINDOWS = _get("IDS_RATE_WINDOWS", {"1m": 60, "5m": 300, "1hr": 3600})

    # Trade anomalies
    TRADE_SIZE_MULTIPLIER = _get("IDS_TRADE_SIZE_MULTIPLIER", 3.0)
    RAPID_ORDER_COUNT = _get("IDS_RAPID_ORDER_COUNT", 5)
    RAPID_ORDER_WINDOW = _get("IDS_RAPID_ORDER_WINDOW", 60)

    # Allowed trading hours (UTC)
    TRADING_START_HOUR = _get("IDS_TRADING_START_HOUR", 0)
    TRADING_END_HOUR = _get("IDS_TRADING_END_HOUR", 23)

    # Login time-of-day anomaly (hours outside normal)
    LOGIN_TYPICAL_START = _get("IDS_LOGIN_TYPICAL_START", 5)
    LOGIN_TYPICAL_END = _get("IDS_LOGIN_TYPICAL_END", 23)

    # API abuse
    API_SCAN_ENDPOINT_THRESHOLD = _get("IDS_API_SCAN_ENDPOINT_THRESHOLD", 20)
    API_FUZZ_PARAM_THRESHOLD = _get("IDS_API_FUZZ_PARAM_THRESHOLD", 15)
    API_ABUSE_WINDOW = _get("IDS_API_ABUSE_WINDOW", 60)


# ===================================================================
# Pattern-based detection
# ===================================================================

class AttackPatterns:
    """Compiled regex patterns for known attack classes."""

    SQL_INJECTION: list[re.Pattern] = [
        re.compile(r"(?i)(?:union\s+select)", re.IGNORECASE),
        re.compile(r"(?i)(?:drop\s+table)", re.IGNORECASE),
        re.compile(r"(?:'|\"|`)\s*(?:;|--|#|/\*)", re.IGNORECASE),
        re.compile(r"(?i)\bor\s+\d+\s*=\s*\d+", re.IGNORECASE),
        re.compile(r"(?i)\band\s+\d+\s*=\s*\d+", re.IGNORECASE),
        re.compile(r"(?i)(?:exec(?:ute)?\s+(?:xp_|sp_))", re.IGNORECASE),
        re.compile(r"(?i)(?:;\s*(?:insert|update|delete|drop|alter|create)\s)", re.IGNORECASE),
        re.compile(r"(?i)(?:0x[0-9a-fA-F]+)", re.IGNORECASE),
        re.compile(r"(?i)(?:char\s*\(\s*\d+)", re.IGNORECASE),
        re.compile(r"(?i)(?:benchmark\s*\()", re.IGNORECASE),
        re.compile(r"(?i)(?:sleep\s*\(\s*\d+)", re.IGNORECASE),
        re.compile(r"(?i)(?:waitfor\s+delay)", re.IGNORECASE),
        re.compile(r"(?i)(?:load_file\s*\()", re.IGNORECASE),
        re.compile(r"(?i)(?:into\s+(?:out|dump)file)", re.IGNORECASE),
        re.compile(r"(?i)\b(?:information_schema|sys(?:objects|columns|tables|indexes))\b", re.IGNORECASE),
    ]

    XSS: list[re.Pattern] = [
        re.compile(r"<\s*script", re.IGNORECASE),
        re.compile(r"javascript\s*:", re.IGNORECASE),
        re.compile(r"(?:on(?:error|load|click|mouse\w+|focus|blur|submit|change)\s*=)", re.IGNORECASE),
        re.compile(r"<\s*(?:iframe|object|embed|applet|form|input|img|svg|body|meta|link|style|base|meta|marquee|video|audio|details|dialog)", re.IGNORECASE),
        re.compile(r"(?:eval\s*\()", re.IGNORECASE),
        re.compile(r"(?:document\s*\.\s*(?:cookie|write|location|domain))", re.IGNORECASE),
        re.compile(r"(?:window\s*\.\s*(?:location|open|eval|execScript))", re.IGNORECASE),
        re.compile(r"(?:expression\s*\()", re.IGNORECASE),
        re.compile(r"(?:<\s*/?\s*(?:div|span|p|a|img|script|body|html|head|style|form|input|button|select|textarea|label)\b[^>]*>)", re.IGNORECASE),
        re.compile(r"(?:vbscript\s*:)", re.IGNORECASE),
        re.compile(r"(?:data\s*:\s*text/html)", re.IGNORECASE),
        re.compile(r"(?:alert\s*\()", re.IGNORECASE),
        re.compile(r"(?:confirm\s*\()", re.IGNORECASE),
        re.compile(r"(?:prompt\s*\()", re.IGNORECASE),
        re.compile(r"(?:src\s*=\s*[\"']?\s*(?:javascript|data|vbscript))", re.IGNORECASE),
    ]

    PATH_TRAVERSAL: list[re.Pattern] = [
        re.compile(r"(?:\.\.[\\/]){1,}", re.IGNORECASE),
        re.compile(r"(?:%2e%2e[%2f%5c]){1,}", re.IGNORECASE),
        re.compile(r"/etc/(?:passwd|shadow|hosts|group|issue|crontab)", re.IGNORECASE),
        re.compile(r"(?:c:[\\/])(?:windows|program\s+files|users)", re.IGNORECASE),
        re.compile(r"(?:proc/self/)", re.IGNORECASE),
        re.compile(r"(?:%00|\\x00)", re.IGNORECASE),
        re.compile(r"(?:\.\.(?:%2f|%5c|%252f|%255c))+", re.IGNORECASE),
        re.compile(r"(?:\.(?:%2f|%5c)){2,}", re.IGNORECASE),
        re.compile(r"(?:boot\.ini|win\.ini|system\.ini)", re.IGNORECASE),
        re.compile(r"(?:/var/log/)", re.IGNORECASE),
    ]

    COMMAND_INJECTION: list[re.Pattern] = [
        re.compile(r"(?:;\s*(?:ls|cat|whoami|id|uname|wget|curl|nc|ncat|python|perl|ruby|bash|sh|cmd|powershell)\b)", re.IGNORECASE),
        re.compile(r"(?:\|\s*(?:ls|cat|whoami|id|uname|wget|curl|nc|ncat|python|perl|ruby|bash|sh|cmd|powershell)\b)", re.IGNORECASE),
        re.compile(r"(?:`[^`]+`)", re.IGNORECASE),
        re.compile(r"(?:\$\([^)]+\))", re.IGNORECASE),
        re.compile(r"(?:&&\s*(?:ls|cat|whoami|id|uname|wget|curl|nc|python|perl|ruby|bash|sh|cmd|powershell)\b)", re.IGNORECASE),
        re.compile(r"(?:\|\|\s*(?:ls|cat|whoami|id|uname|wget|curl|nc|python|perl|ruby|bash|sh|cmd|powershell)\b)", re.IGNORECASE),
        re.compile(r"(?:>\s*/(?:dev|tmp|etc)/)", re.IGNORECASE),
        re.compile(r"(?:<\s*/(?:dev|tmp|etc)/)", re.IGNORECASE),
        re.compile(r"(?:;\s*(?:mkfifo|nc\s+-|ncat\s+-|socat)\b)", re.IGNORECASE),
        re.compile(r"(?:\|\s*(?:mkfifo|nc\s+-|ncat\s+-|socat)\b)", re.IGNORECASE),
        re.compile(r"(?:\$\{IFS\})", re.IGNORECASE),
    ]

    SSRF: list[re.Pattern] = [
        re.compile(r"(?:https?://\s*(?:127\.0\.0\.1|localhost|0\.0\.0\.0|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+|169\.254\.\d+\.\d+))", re.IGNORECASE),
        re.compile(r"(?:https?://\[?(?:::1|0:0:0:0:0:0:0:1)\]?)", re.IGNORECASE),
        re.compile(r"(?:https?://(?:metadata\.google\.internal|169\.254\.169\.254))", re.IGNORECASE),
        re.compile(r"(?:file://)", re.IGNORECASE),
        re.compile(r"(?:gopher://)", re.IGNORECASE),
        re.compile(r"(?:dict://)", re.IGNORECASE),
        re.compile(r"(?:https?://[a-z0-9\-]+\.internal)", re.IGNORECASE),
    ]

    LDAP_INJECTION: list[re.Pattern] = [
        re.compile(r"(?:\*\)\s*\(\s*(?:objectclass|cn|uid|ou)\s*=)", re.IGNORECASE),
        re.compile(r"(?:\(\s*(?:objectclass|cn|uid|ou)\s*=\s*\*\s*\))", re.IGNORECASE),
        re.compile(r"(?:\)\s*\(\s*\(\s*\)\s*\))", re.IGNORECASE),
        re.compile(r"(?:\)\s*\|\s*\(\s*\))", re.IGNORECASE),
        re.compile(r"(?:\\2a|\\28|\\29|\\5c)", re.IGNORECASE),
        re.compile(r"(?:\(\s*\|\s*(?:uid|cn|ou)\s*=\s*)", re.IGNORECASE),
    ]


# ===================================================================
# Helper: log a SecurityEvent
# ===================================================================

def _log_event(
    event_type: str,
    threat_level: int,
    *,
    user_id: str = "",
    ip_address: str | None = None,
    user_agent: str = "",
    details: dict | None = None,
    endpoint: str = "",
    method: str = "",
    action_taken: str = "allowed",
) -> SecurityEvent:
    """Create and persist a SecurityEvent. Errors are swallowed (never block)."""
    try:
        event = SecurityEvent(
            event_type=event_type,
            threat_level=threat_level,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            endpoint=endpoint,
            method=method,
            action_taken=action_taken,
        )
        event.save()
        return event
    except Exception:
        logger.exception("Failed to persist SecurityEvent %s", event_type)
        return None  # type: ignore[return-value]


# ===================================================================
# RateAnalyzer
# ===================================================================

class RateAnalyzer:
    """
    Tracks request rates per IP/user and detects spikes.

    Internally stores timestamps in a list per key, pruning entries older
    than the longest configured window.
    """

    def __init__(self):
        self._lock = Lock()
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def _max_window(self) -> int:
        return max(_Config.RATE_WINDOWS.values()) if _Config.RATE_WINDOWS else 3600

    def record(self, key: str, now: float | None = None) -> None:
        now = now or time.time()
        with self._lock:
            bucket = self._buckets[key]
            cutoff = now - self._max_window()
            self._buckets[key] = [t for t in bucket if t > cutoff]
            bucket.append(now)

    def count_in_window(self, key: str, window_seconds: int, now: float | None = None) -> int:
        now = now or time.time()
        with self._lock:
            bucket = self._buckets[key]
            cutoff = now - window_seconds
            return sum(1 for t in bucket if t > cutoff)

    def detect_spike(self, key: str, now: float | None = None) -> dict | None:
        """
        Compare the most recent 1-minute count against the average of
        previous windows.  Returns threat info if rate > multiplier * avg.
        """
        now = now or time.time()
        with self._lock:
            bucket = self._buckets[key]
            cutoff = now - self._max_window()
            timestamps = [t for t in bucket if t > cutoff]

        if len(timestamps) < 10:
            return None

        current_minute = sum(1 for t in timestamps if t > now - 60)

        # Compute average rate over prior windows
        window_counts = []
        for w_name, w_sec in _Config.RATE_WINDOWS.items():
            if w_sec <= 60:
                continue
            prev_count = sum(1 for t in timestamps if now - w_sec < t <= now - 60)
            window_counts.append(prev_count / (w_sec / 60))

        if not window_counts:
            return None

        avg_rate_per_min = sum(window_counts) / len(window_counts)
        if avg_rate_per_min == 0:
            return None

        if current_minute > avg_rate_per_min * _Config.RATE_SPIKE_MULTIPLIER:
            return {
                "type": "rate_spike",
                "current_per_min": current_minute,
                "avg_per_min": round(avg_rate_per_min, 2),
                "multiplier": round(current_minute / avg_rate_per_min, 2),
            }
        return None

    def detect_sustained(self, key: str, now: float | None = None) -> dict | None:
        """Detect sustained high rate over the full 1-hour window."""
        now = now or time.time()
        max_w = self._max_window()
        count = self.count_in_window(key, max_w, now)
        threshold = _Config.RATE_WINDOWS.get("1hr", 3600) * 0.5  # >50% of window
        if count > threshold:
            return {
                "type": "sustained_high_rate",
                "count_1hr": count,
                "threshold": int(threshold),
            }
        return None

    def analyze(self, key: str, now: float | None = None) -> dict | None:
        spike = self.detect_spike(key, now)
        if spike:
            return spike
        return self.detect_sustained(key, now)

    def cleanup(self) -> None:
        with self._lock:
            cutoff = time.time() - self._max_window()
            for key in list(self._buckets):
                self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]
                if not self._buckets[key]:
                    del self._buckets[key]


# ===================================================================
# LoginAnalyzer
# ===================================================================

class LoginAnalyzer:
    """Tracks login success/failure patterns per user and per IP."""

    def __init__(self):
        self._lock = Lock()
        # user_id -> list[(timestamp, success)]
        self._user_logins: dict[str, list[tuple[float, bool]]] = defaultdict(list)
        # ip -> list[(timestamp, user_id)]
        self._ip_logins: dict[str, list[tuple[float, str]]] = defaultdict(list)

    def record(self, user_id: str, ip: str, success: bool, now: float | None = None) -> None:
        now = now or time.time()
        with self._lock:
            self._user_logins[user_id].append((now, success))
            self._ip_logins[ip].append((now, user_id))

    def detect_brute_force(self, user_id: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        cutoff = now - _Config.BRUTE_FORCE_WINDOW
        with self._lock:
            attempts = self._user_logins.get(user_id, [])
        recent_failures = [
            t for t, ok in attempts if not ok and t > cutoff
        ]
        if len(recent_failures) >= _Config.BRUTE_FORCE_FAILURES:
            return {
                "type": "brute_force",
                "user_id": user_id,
                "failures_in_window": len(recent_failures),
                "window_seconds": _Config.BRUTE_FORCE_WINDOW,
                "threshold": _Config.BRUTE_FORCE_FAILURES,
            }
        return None

    def detect_credential_stuffing(self, ip: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        cutoff = now - _Config.STUFFING_WINDOW
        with self._lock:
            logins = self._ip_logins.get(ip, [])
        unique_users = {uid for t, uid in logins if t > cutoff}
        if len(unique_users) >= _Config.STUFFING_IP_THRESHOLD:
            return {
                "type": "credential_stuffing",
                "ip": ip,
                "unique_users_attempted": len(unique_users),
                "window_seconds": _Config.STUFFING_WINDOW,
                "threshold": _Config.STUFFING_IP_THRESHOLD,
            }
        return None

    def detect_time_anomaly(self, user_id: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        hour = timezone.datetime.fromtimestamp(now, tz=timezone.utc).hour
        if not (_Config.LOGIN_TYPICAL_START <= hour < _Config.LOGIN_TYPICAL_END):
            return {
                "type": "unusual_login_time",
                "user_id": user_id,
                "hour_utc": hour,
                "typical_range": f"{_Config.LOGIN_TYPICAL_START}:00-{_Config.LOGIN_TYPICAL_END}:00 UTC",
            }
        return None

    def analyze(self, user_id: str, ip: str, success: bool, now: float | None = None) -> list[dict]:
        now = now or time.time()
        self.record(user_id, ip, success, now)
        threats: list[dict] = []

        if not success:
            bf = self.detect_brute_force(user_id, now)
            if bf:
                threats.append(bf)

        cs = self.detect_credential_stuffing(ip, now)
        if cs:
            threats.append(cs)

        ta = self.detect_time_anomaly(user_id, now)
        if ta:
            threats.append(ta)

        return threats

    def cleanup(self, max_age: int = 7200) -> None:
        cutoff = time.time() - max_age
        with self._lock:
            for uid in list(self._user_logins):
                self._user_logins[uid] = [(t, s) for t, s in self._user_logins[uid] if t > cutoff]
                if not self._user_logins[uid]:
                    del self._user_logins[uid]
            for ip in list(self._ip_logins):
                self._ip_logins[ip] = [(t, u) for t, u in self._ip_logins[ip] if t > cutoff]
                if not self._ip_logins[ip]:
                    del self._ip_logins[ip]


# ===================================================================
# TradeAnalyzer
# ===================================================================

class TradeAnalyzer:
    """Detects anomalous trading behaviour."""

    def __init__(self):
        self._lock = Lock()
        # user_id -> list[(timestamp, volume, symbol)]
        self._trades: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
        # user_id -> list[(timestamp, action, symbol)]
        self._order_modifications: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
        # user_id -> average historical volume
        self._avg_volumes: dict[str, float] = {}
        # user_id -> (avg_volume, sample_count)
        self._volume_stats: dict[str, tuple[float, int]] = {}

    def record_trade(self, user_id: str, volume: float, symbol: str, now: float | None = None) -> None:
        now = now or time.time()
        with self._lock:
            self._trades[user_id].append((now, volume, symbol))
            self._update_volume_stats(user_id, volume)

    def record_order_modification(self, user_id: str, action: str, symbol: str, now: float | None = None) -> None:
        now = now or time.time()
        with self._lock:
            self._order_modifications[user_id].append((now, action, symbol))

    def _update_volume_stats(self, user_id: str, volume: float) -> None:
        avg, count = self._volume_stats.get(user_id, (0.0, 0))
        new_avg = (avg * count + volume) / (count + 1)
        self._volume_stats[user_id] = (new_avg, count + 1)

    def detect_unusual_size(self, user_id: str, volume: float, now: float | None = None) -> dict | None:
        now = now or time.time()
        with self._lock:
            stats = self._volume_stats.get(user_id)
        if not stats or stats[1] < 5:
            return None
        avg_vol = stats[0]
        if avg_vol > 0 and volume > avg_vol * _Config.TRADE_SIZE_MULTIPLIER:
            return {
                "type": "unusual_position_size",
                "user_id": user_id,
                "volume": float(volume),
                "avg_volume": round(avg_vol, 4),
                "multiplier": round(volume / avg_vol, 2),
            }
        return None

    def detect_rapid_orders(self, user_id: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        cutoff = now - _Config.RAPID_ORDER_WINDOW
        with self._lock:
            mods = self._order_modifications.get(user_id, [])
        recent = [(t, a, s) for t, a, s in mods if t > cutoff]
        if len(recent) >= _Config.RAPID_ORDER_COUNT:
            return {
                "type": "rapid_order_modifications",
                "user_id": user_id,
                "modifications_in_window": len(recent),
                "window_seconds": _Config.RAPID_ORDER_WINDOW,
                "threshold": _Config.RAPID_ORDER_COUNT,
                "actions": [a for _, a, _ in recent[-5:]],
            }
        return None

    def detect_outside_session(self, now: float | None = None) -> dict | None:
        now = now or time.time()
        hour = timezone.datetime.fromtimestamp(now, tz=timezone.utc).hour
        if not (_Config.TRADING_START_HOUR <= hour < _Config.TRADING_END_HOUR):
            return {
                "type": "trading_outside_allowed_session",
                "hour_utc": hour,
                "allowed_range": f"{_Config.TRADING_START_HOUR}:00-{_Config.TRADING_END_HOUR}:00 UTC",
            }
        return None

    def detect_correlation_anomaly(
        self,
        user_id: str,
        symbol: str,
        position_type: str,
        existing_positions: list[dict],
    ) -> dict | None:
        """
        Detect when a new trade correlates too strongly with existing
        positions (all same direction on correlated instruments).
        """
        if not existing_positions:
            return None
        same_direction = sum(
            1 for p in existing_positions
            if p.get("position_type") == position_type
        )
        total = len(existing_positions)
        if total > 0 and same_direction / total > 0.8 and total >= 3:
            return {
                "type": "correlation_anomaly",
                "user_id": user_id,
                "symbol": symbol,
                "position_type": position_type,
                "same_direction_ratio": round(same_direction / total, 2),
                "existing_positions": total,
            }
        return None

    def analyze_trade(
        self,
        user_id: str,
        volume: float,
        symbol: str,
        position_type: str,
        existing_positions: list[dict] | None = None,
        now: float | None = None,
    ) -> list[dict]:
        now = now or time.time()
        self.record_trade(user_id, volume, symbol, now)
        threats: list[dict] = []

        us = self.detect_unusual_size(user_id, volume, now)
        if us:
            threats.append(us)

        ro = self.detect_rapid_orders(user_id, now)
        if ro:
            threats.append(ro)

        os_threat = self.detect_outside_session(now)
        if os_threat:
            threats.append(os_threat)

        if existing_positions:
            ca = self.detect_correlation_anomaly(user_id, symbol, position_type, existing_positions)
            if ca:
                threats.append(ca)

        return threats

    def cleanup(self, max_age: int = 7200) -> None:
        cutoff = time.time() - max_age
        with self._lock:
            for uid in list(self._trades):
                self._trades[uid] = [(t, v, s) for t, v, s in self._trades[uid] if t > cutoff]
                if not self._trades[uid]:
                    del self._trades[uid]
            for uid in list(self._order_modifications):
                self._order_modifications[uid] = [
                    (t, a, s) for t, a, s in self._order_modifications[uid] if t > cutoff
                ]
                if not self._order_modifications[uid]:
                    del self._order_modifications[uid]


# ===================================================================
# API abuse detector (endpoint scanning / parameter fuzzing)
# ===================================================================

class APIAbuseAnalyzer:
    """Detects endpoint scanning and parameter fuzzing."""

    def __init__(self):
        self._lock = Lock()
        # ip -> list[(timestamp, endpoint)]
        self._endpoint_hits: dict[str, list[tuple[float, str]]] = defaultdict(list)
        # ip -> list[(timestamp, param_name)]
        self._param_hits: dict[str, list[tuple[float, str]]] = defaultdict(list)

    def record_endpoint(self, ip: str, endpoint: str, now: float | None = None) -> None:
        now = now or time.time()
        with self._lock:
            self._endpoint_hits[ip].append((now, endpoint))

    def record_param(self, ip: str, param_name: str, now: float | None = None) -> None:
        now = now or time.time()
        with self._lock:
            self._param_hits[ip].append((now, param_name))

    def detect_scanning(self, ip: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        cutoff = now - _Config.API_ABUSE_WINDOW
        with self._lock:
            hits = self._endpoint_hits.get(ip, [])
        unique_endpoints = {ep for t, ep in hits if t > cutoff}
        if len(unique_endpoints) >= _Config.API_SCAN_ENDPOINT_THRESHOLD:
            return {
                "type": "endpoint_scanning",
                "ip": ip,
                "unique_endpoints": len(unique_endpoints),
                "window_seconds": _Config.API_ABUSE_WINDOW,
                "threshold": _Config.API_SCAN_ENDPOINT_THRESHOLD,
                "sample_endpoints": list(unique_endpoints)[:10],
            }
        return None

    def detect_fuzzing(self, ip: str, now: float | None = None) -> dict | None:
        now = now or time.time()
        cutoff = now - _Config.API_ABUSE_WINDOW
        with self._lock:
            hits = self._param_hits.get(ip, [])
        unique_params = {p for t, p in hits if t > cutoff}
        if len(unique_params) >= _Config.API_FUZZ_PARAM_THRESHOLD:
            return {
                "type": "parameter_fuzzing",
                "ip": ip,
                "unique_params": len(unique_params),
                "window_seconds": _Config.API_ABUSE_WINDOW,
                "threshold": _Config.API_FUZZ_PARAM_THRESHOLD,
                "sample_params": list(unique_params)[:10],
            }
        return None

    def analyze(self, ip: str, now: float | None = None) -> list[dict]:
        threats: list[dict] = []
        sc = self.detect_scanning(ip, now)
        if sc:
            threats.append(sc)
        fz = self.detect_fuzzing(ip, now)
        if fz:
            threats.append(fz)
        return threats

    def cleanup(self, max_age: int = 3600) -> None:
        cutoff = time.time() - max_age
        with self._lock:
            for ip in list(self._endpoint_hits):
                self._endpoint_hits[ip] = [(t, e) for t, e in self._endpoint_hits[ip] if t > cutoff]
                if not self._endpoint_hits[ip]:
                    del self._endpoint_hits[ip]
            for ip in list(self._param_hits):
                self._param_hits[ip] = [(t, p) for t, p in self._param_hits[ip] if t > cutoff]
                if not self._param_hits[ip]:
                    del self._param_hits[ip]


# ===================================================================
# Main IDS singleton
# ===================================================================

class IntrusionDetectionSystem:
    """
    Singleton IDS/IPS engine.

    Usage::

        ids = IntrusionDetectionSystem.get_instance()
        result = ids.analyze_request(request)
    """

    _instance: "IntrusionDetectionSystem | None" = None
    _lock = Lock()

    def __init__(self):
        self.rate_analyzer = RateAnalyzer()
        self.login_analyzer = LoginAnalyzer()
        self.trade_analyzer = TradeAnalyzer()
        self.api_abuse = APIAbuseAnalyzer()
        self._custom_rules: dict[str, list[re.Pattern]] = {}
        logger.info("IntrusionDetectionSystem initialised")

    @classmethod
    def get_instance(cls) -> "IntrusionDetectionSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Pattern matching helpers
    # ------------------------------------------------------------------

    def _check_patterns(self, text: str) -> list[dict]:
        """Run all attack patterns against *text* and return matches."""
        hits: list[dict] = []
        pattern_groups = {
            "sql_injection": AttackPatterns.SQL_INJECTION,
            "xss": AttackPatterns.XSS,
            "path_traversal": AttackPatterns.PATH_TRAVERSAL,
            "command_injection": AttackPatterns.COMMAND_INJECTION,
            "ssrf": AttackPatterns.SSRF,
            "ldap_injection": AttackPatterns.LDAP_INJECTION,
        }
        # Include any custom rules
        for name, patterns in self._custom_rules.items():
            pattern_groups[name] = patterns

        for group_name, patterns in pattern_groups.items():
            for idx, pattern in enumerate(patterns):
                if pattern.search(text):
                    hits.append({
                        "attack_type": group_name,
                        "pattern_index": idx,
                        "matched_in": text[:200],
                    })
        return hits

    def _max_threat_level(self, hits: list[dict]) -> int:
        mapping = {
            "sql_injection": ThreatLevel.CRITICAL,
            "command_injection": ThreatLevel.CRITICAL,
            "path_traversal": ThreatLevel.HIGH,
            "xss": ThreatLevel.HIGH,
            "ssrf": ThreatLevel.HIGH,
            "ldap_injection": ThreatLevel.MEDIUM,
        }
        if not hits:
            return ThreatLevel.INFO
        return max(mapping.get(h["attack_type"], ThreatLevel.LOW) for h in hits)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_request(self, request: Any) -> tuple[int, dict]:
        """
        Analyse an incoming Django request.

        Returns ``(ThreatLevel, details_dict)``.

        ``details_dict`` contains:
        - ``blocked``: bool
        - ``reasons``: list of detected issues
        - ``rate_threat``: rate-limiting info (or None)
        - ``api_abuse_threats``: list of API abuse detections
        """
        ip = self._extract_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        method = request.method
        path = request.path
        user_id = ""
        if hasattr(request, "user") and request.user and request.user.is_authenticated:
            user_id = str(request.user.pk)

        # -- Check blocked IP
        if self._is_blocked_ip(ip):
            _log_event(
                "ids_blocked_ip",
                ThreatLevel.CRITICAL,
                ip_address=ip,
                user_agent=user_agent,
                details={"path": path, "method": method},
                endpoint=path,
                method=method,
                action_taken="blocked",
            )
            return ThreatLevel.CRITICAL, {
                "blocked": True,
                "reasons": ["blocked_ip"],
                "rate_threat": None,
                "api_abuse_threats": [],
            }

        reasons: list[dict] = []
        all_hits: list[dict] = []

        # -- Inspect URL
        all_hits.extend(self._check_patterns(path))

        # -- Inspect query parameters
        if hasattr(request, "GET") and request.GET:
            for key, val in request.GET.items():
                all_hits.extend(self._check_patterns(f"{key}={val}"))

        # -- Inspect request body (safe read)
        body = self._read_body(request)
        if body:
            all_hits.extend(self._check_patterns(body))

        # -- Inspect headers
        for hdr in ("HTTP_REFERER", "HTTP_X_FORWARDED_FOR", "HTTP_COOKIE"):
            hdr_val = request.META.get(hdr, "")
            if hdr_val:
                all_hits.extend(self._check_patterns(hdr_val))

        if all_hits:
            reasons.extend(all_hits)

        # -- Rate analysis
        rate_key_ip = f"ip:{ip}"
        rate_key_user = f"user:{user_id}" if user_id else None
        self.rate_analyzer.record(rate_key_ip)
        if rate_key_user:
            self.rate_analyzer.record(rate_key_user)

        rate_threat = self.rate_analyzer.analyze(rate_key_ip)
        if not rate_threat and rate_key_user:
            rate_threat = self.rate_analyzer.analyze(rate_key_user)
        if rate_threat:
            reasons.append(rate_threat)

        # -- API abuse
        self.api_abuse.record_endpoint(ip, path)
        if hasattr(request, "GET") and request.GET:
            for key in request.GET:
                self.api_abuse.record_param(ip, key)
        if hasattr(request, "POST") and request.POST:
            for key in request.POST:
                self.api_abuse.record_param(ip, key)

        api_abuse_threats = self.api_abuse.analyze(ip)
        reasons.extend(api_abuse_threats)

        # -- Determine overall threat level
        threat_level = self._max_threat_level(all_hits)
        if rate_threat:
            threat_level = max(threat_level, ThreatLevel.MEDIUM)
        for at in api_abuse_threats:
            threat_level = max(threat_level, ThreatLevel.LOW)

        blocked = threat_level >= ThreatLevel.HIGH
        action = "blocked" if blocked else "allowed"

        if all_hits or rate_threat or api_abuse_threats:
            _log_event(
                "ids_alert",
                threat_level,
                user_id=user_id,
                ip_address=ip,
                user_agent=user_agent,
                details={
                    "hits": reasons[:20],
                    "total_hits": len(reasons),
                },
                endpoint=path,
                method=method,
                action_taken=action,
            )

        return threat_level, {
            "blocked": blocked,
            "reasons": reasons,
            "rate_threat": rate_threat,
            "api_abuse_threats": api_abuse_threats,
        }

    def analyze_trade(
        self,
        trade_data: dict,
        existing_positions: list[dict] | None = None,
    ) -> tuple[int, dict]:
        """
        Analyse a proposed trade for anomalies.

        ``trade_data`` must contain: ``user_id``, ``volume``, ``symbol``, ``position_type``.

        Returns ``(ThreatLevel, details_dict)``.
        """
        user_id = str(trade_data.get("user_id", ""))
        volume = float(trade_data.get("volume", 0))
        symbol = str(trade_data.get("symbol", ""))
        position_type = str(trade_data.get("position_type", ""))

        threats = self.trade_analyzer.analyze_trade(
            user_id, volume, symbol, position_type, existing_positions
        )

        threat_level = ThreatLevel.INFO
        blocked = False
        for t in threats:
            if t.get("type") == "unusual_position_size":
                threat_level = max(threat_level, ThreatLevel.HIGH)
                blocked = True
            elif t.get("type") == "rapid_order_modifications":
                threat_level = max(threat_level, ThreatLevel.MEDIUM)
            elif t.get("type") == "trading_outside_allowed_session":
                threat_level = max(threat_level, ThreatLevel.MEDIUM)
            elif t.get("type") == "correlation_anomaly":
                threat_level = max(threat_level, ThreatLevel.LOW)

        if threats:
            _log_event(
                "suspicious_trading",
                threat_level,
                user_id=user_id,
                details={
                    "trade_data": {k: str(v) for k, v in trade_data.items()},
                    "threats": threats,
                },
                action_taken="blocked" if blocked else "allowed",
            )

        return threat_level, {
            "blocked": blocked,
            "threats": threats,
        }

    def analyze_login(self, user_id: str, ip: str, success: bool) -> tuple[int, dict]:
        """
        Analyse a login attempt.

        Returns ``(ThreatLevel, details_dict)``.
        """
        threats = self.login_analyzer.analyze(user_id, ip, success)

        threat_level = ThreatLevel.INFO
        blocked = False
        for t in threats:
            if t.get("type") == "brute_force":
                threat_level = max(threat_level, ThreatLevel.HIGH)
                blocked = True
            elif t.get("type") == "credential_stuffing":
                threat_level = max(threat_level, ThreatLevel.CRITICAL)
                blocked = True
            elif t.get("type") == "unusual_login_time":
                threat_level = max(threat_level, ThreatLevel.LOW)

        event_type = "login_success" if success else "login_failure"
        if threats:
            event_type = "ids_alert"

        if threats or not success:
            _log_event(
                event_type,
                threat_level,
                user_id=user_id,
                ip_address=ip,
                details={"success": success, "threats": threats},
                action_taken="blocked" if blocked else "allowed",
            )

        return threat_level, {
            "blocked": blocked,
            "threats": threats,
        }

    def update_rules(self, new_rules: dict[str, list[str]]) -> int:
        """
        Reload detection patterns from *new_rules*.

        ``new_rules`` maps category names to lists of regex strings.

        Returns the number of compiled patterns added.
        """
        count = 0
        for category, raw_patterns in new_rules.items():
            compiled = []
            for raw in raw_patterns:
                try:
                    compiled.append(re.compile(raw, re.IGNORECASE))
                except re.error:
                    logger.warning("Invalid regex in IDS rule '%s': %s", category, raw)
            if compiled:
                self._custom_rules[category] = compiled
                count += len(compiled)
                logger.info("Loaded %d custom patterns for category '%s'", len(compiled), category)
        return count

    def cleanup(self) -> None:
        """Prune stale entries from all internal analyzers."""
        self.rate_analyzer.cleanup()
        self.login_analyzer.cleanup()
        self.trade_analyzer.cleanup()
        self.api_abuse.cleanup()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_ip(request: Any) -> str:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")

    @staticmethod
    def _is_blocked_ip(ip: str) -> bool:
        try:
            record = BlockedIP.objects.get(ip_address=ip, is_active=True)
            if record.is_expired():
                return False
            return True
        except BlockedIP.DoesNotExist:
            return False
        except Exception:
            logger.debug("BlockedIP lookup failed (DB may be empty)")
            return False

    @staticmethod
    def _read_body(request: Any) -> str:
        """Safely read request body, limited to 1 MB to avoid memory abuse."""
        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode("utf-8", errors="replace")
            return body[:1_048_576]
        except Exception:
            return ""
