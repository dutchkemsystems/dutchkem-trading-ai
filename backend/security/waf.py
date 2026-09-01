"""
V5 Web Application Firewall (WAF) Middleware.

Provides request sanitization, attack-pattern detection, rate limiting,
blocked-IP enforcement, and Content-Type / payload-size validation.
All blocked requests are logged as SecurityEvent records.
"""

import logging
import re
import time
import unicodedata
from collections import defaultdict
from threading import Lock
from typing import Any
from urllib.parse import unquote

from django.conf import settings
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from .models import BlockedIP, SecurityEvent, ThreatLevel

logger = logging.getLogger("security.waf")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _cfg(name: str, default: Any) -> Any:
    return getattr(settings, name, default)


class WAFConfig:
    ENABLED = _cfg("WAF_ENABLED", True)
    RATE_LIMIT = _cfg("WAF_RATE_LIMIT", 100)  # requests per minute per IP
    BLOCK_DURATION = _cfg("WAF_BLOCK_DURATION", 3600)  # seconds
    MAX_BODY_SIZE = _cfg("WAF_MAX_BODY_SIZE", 10 * 1024 * 1024)  # 10 MB
    ALLOWED_CONTENT_TYPES = _cfg("WAF_ALLOWED_CONTENT_TYPES", [
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
        "application/octet-stream",
    ])
    RATE_LIMITS_PER_ENDPOINT = _cfg("WAF_RATE_LIMITS_PER_ENDPOINT", {
        "/api/v1/auth/login/": 10,
        "/api/v1/auth/token/refresh/": 20,
    })
    RATE_WINDOW = _cfg("WAF_RATE_WINDOW", 60)  # seconds
    LOG_BLOCKED = _cfg("WAF_LOG_BLOCKED", True)
    BLOCK_RESPONSE_MESSAGE = _cfg(
        "WAF_BLOCK_RESPONSE_MESSAGE",
        "Request blocked. If you believe this is an error, contact support.",
    )


# ===================================================================
# RequestSanitizer
# ===================================================================

class RequestSanitizer:
    """Cleans and normalizes incoming request data."""

    # Control characters (excluding normal whitespace \t \n \r)
    _CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    @staticmethod
    def sanitize(value: str) -> str:
        if not isinstance(value, str):
            return value
        # 1. Decode double-encoded payloads (e.g. %2527 → %27 → ')
        decoded = value
        for _ in range(3):
            new_decoded = unquote(decoded)
            if new_decoded == decoded:
                break
            decoded = new_decoded
        # 2. Strip null bytes and control characters
        decoded = RequestSanitizer._CTRL_RE.sub("", decoded)
        # 3. Normalize Unicode (NFKC normalisation)
        decoded = unicodedata.normalize("NFKC", decoded)
        return decoded

    @staticmethod
    def sanitize_dict(data: dict) -> dict:
        return {k: RequestSanitizer.sanitize(v) if isinstance(v, str) else v for k, v in data.items()}

    @staticmethod
    def sanitize_list(values: list) -> list:
        return [RequestSanitizer.sanitize(v) if isinstance(v, str) else v for v in values]


# ===================================================================
# AttackPatternDetector
# ===================================================================

class AttackPatternDetector:
    """
    Regex-based detector for common web-attack patterns.
    Returns list of matching threat descriptors.
    """

    SQL_INJECTION: list[re.Pattern] = [
        re.compile(r"(?i)(?:union[\s]+select)", re.IGNORECASE),
        re.compile(r"(?i)(?:drop[\s]+table)", re.IGNORECASE),
        re.compile(r"(?:'|\"|`)\s*;\s*(?:--|#|/\*)", re.IGNORECASE),
        re.compile(r"(?i)\bor\s+[\d\"']+\s*=\s*[\d\"']+"),
        re.compile(r"(?i)\band\s+[\d\"']+\s*=\s*[\d\"']+", re.IGNORECASE),
        re.compile(r"(?i)(?:exec(?:ute)?[\s]+(?:xp_|sp_))", re.IGNORECASE),
        re.compile(r"(?i)(?:;\s*(?:insert|update|delete|drop|alter|create|rename|truncate)\s)", re.IGNORECASE),
        re.compile(r"(?i)(?:0x[0-9a-fA-F]{8,})", re.IGNORECASE),
        re.compile(r"(?i)(?:char\s*\(\s*\d{2,3}\s*\))", re.IGNORECASE),
        re.compile(r"(?i)(?:benchmark\s*\(\s*\d+)", re.IGNORECASE),
        re.compile(r"(?i)(?:sleep\s*\(\s*\d+\s*\))", re.IGNORECASE),
        re.compile(r"(?i)(?:waitfor\s+delay\s+['\"]\d+:\d+:\d+)", re.IGNORECASE),
        re.compile(r"(?i)(?:load_file\s*\()", re.IGNORECASE),
        re.compile(r"(?i)(?:into\s+(?:out|dump)\s*file)", re.IGNORECASE),
        re.compile(r"(?i)\b(?:information_schema|sys(?:objects|columns|tables|indexes))\b", re.IGNORECASE),
        re.compile(r"(?i)(?:select\s+(?:\*\s+)?from\s+\w+)", re.IGNORECASE),
        re.compile(r"(?i)(?:select\s+(?:@@\w+|version\s*\(\)))", re.IGNORECASE),
    ]

    XSS: list[re.Pattern] = [
        re.compile(r"<\s*script[\s>]", re.IGNORECASE),
        re.compile(r"javascript\s*:", re.IGNORECASE),
        re.compile(r"(?:on(?:error|load|click|dblclick|mouse\w+|focus|blur|submit|change|input|keydown|keyup|keypress)\s*=)", re.IGNORECASE),
        re.compile(r"<\s*(?:iframe|object|embed|applet|form|input|img|svg|body|meta|link|style|base|marquee|video|audio|details|dialog)\b[^>]*>", re.IGNORECASE),
        re.compile(r"(?:eval\s*\()", re.IGNORECASE),
        re.compile(r"(?:document\s*\.\s*(?:cookie|write|location|domain|createElement))", re.IGNORECASE),
        re.compile(r"(?:window\s*\.\s*(?:location|open|eval|execScript))", re.IGNORECASE),
        re.compile(r"(?:expression\s*\()", re.IGNORECASE),
        re.compile(r"(?:<\s*/?\s*(?:div|span|p|a|img|script|body|html|head|style|form|input|button|select|textarea|label|table|tr|td|th|ul|ol|li|pre|code|b|i|u|strong|em|font|center|h[1-6])\b[^>]*>)", re.IGNORECASE),
        re.compile(r"(?:vbscript\s*:)", re.IGNORECASE),
        re.compile(r"(?:data\s*:\s*text/html)", re.IGNORECASE),
        re.compile(r"(?:alert\s*\()", re.IGNORECASE),
        re.compile(r"(?:confirm\s*\()", re.IGNORECASE),
        re.compile(r"(?:prompt\s*\()", re.IGNORECASE),
        re.compile(r"(?:src\s*=\s*[\"']?\s*(?:javascript|data|vbscript))", re.IGNORECASE),
        re.compile(r"(?:fromCharCode)", re.IGNORECASE),
        re.compile(r"(?:String\.fromCharCode)", re.IGNORECASE),
        re.compile(r"(?:atob\s*\()", re.IGNORECASE),
        re.compile(r"(?:btoa\s*\()", re.IGNORECASE),
    ]

    PATH_TRAVERSAL: list[re.Pattern] = [
        re.compile(r"(?:\.\.[\\/]){1,}", re.IGNORECASE),
        re.compile(r"(?:%2e%2e[%2f%5c]){1,}", re.IGNORECASE),
        re.compile(r"/etc/(?:passwd|shadow|hosts|group|issue|crontab|fstab|os-release)", re.IGNORECASE),
        re.compile(r"(?:c:[\\/])(?:windows|program\s+files|users)", re.IGNORECASE),
        re.compile(r"(?:proc/self/)", re.IGNORECASE),
        re.compile(r"(?:%00|\\x00)", re.IGNORECASE),
        re.compile(r"(?:\.\.(?:%2f|%5c|%252f|%255c))+", re.IGNORECASE),
        re.compile(r"(?:boot\.ini|win\.ini|system\.ini|ntldr)", re.IGNORECASE),
        re.compile(r"(?:/var/log/)", re.IGNORECASE),
        re.compile(r"(?:\.\./\.\./)", re.IGNORECASE),
        re.compile(r"(?:\\\.\\\.\\)", re.IGNORECASE),
    ]

    COMMAND_INJECTION: list[re.Pattern] = [
        re.compile(r"(?:;\s*(?:ls|cat|whoami|id|uname|wget|curl|nc|ncat|python|perl|ruby|bash|sh|cmd|powershell|netcat|telnet)\b)", re.IGNORECASE),
        re.compile(r"(?:\|\s*(?:ls|cat|whoami|id|uname|wget|curl|nc|ncat|python|perl|ruby|bash|sh|cmd|powershell|netcat|telnet)\b)", re.IGNORECASE),
        re.compile(r"(?:`[^`]{1,500}`)", re.IGNORECASE),
        re.compile(r"(?:\$\([^)]{1,500}\))", re.IGNORECASE),
        re.compile(r"(?:&&\s*(?:ls|cat|whoami|id|uname|wget|curl|nc|python|perl|ruby|bash|sh|cmd|powershell)\b)", re.IGNORECASE),
        re.compile(r"(?:\|\|\s*(?:ls|cat|whoami|id|uname|wget|curl|nc|python|perl|ruby|bash|sh|cmd|powershell)\b)", re.IGNORECASE),
        re.compile(r"(?:>\s*/(?:dev|tmp|etc)/)", re.IGNORECASE),
        re.compile(r"(?:;\s*(?:mkfifo|nc\s+-l|ncat\s+-l|socat)\b)", re.IGNORECASE),
        re.compile(r"(?:\|\s*(?:mkfifo|nc\s+-l|ncat\s+-l|socat)\b)", re.IGNORECASE),
        re.compile(r"(?:\$\{IFS\})", re.IGNORECASE),
        re.compile(r"(?:\\x[0-9a-fA-F]{2})", re.IGNORECASE),
        re.compile(r"(?:\benv\b.*\b(?:/bin/(?:ba)?sh|/usr/bin/env)\b)", re.IGNORECASE),
    ]

    SSRF: list[re.Pattern] = [
        re.compile(r"(?:https?://\s*(?:127\.0\.0\.1|localhost|0\.0\.0\.0|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+|169\.254\.\d+\.\d+))", re.IGNORECASE),
        re.compile(r"(?:https?://\[?(?:::1|0:0:0:0:0:0:0:1)\]?)", re.IGNORECASE),
        re.compile(r"(?:https?://(?:metadata\.google\.internal|169\.254\.169\.254))", re.IGNORECASE),
        re.compile(r"(?:file://)", re.IGNORECASE),
        re.compile(r"(?:gopher://)", re.IGNORECASE),
        re.compile(r"(?:dict://)", re.IGNORECASE),
        re.compile(r"(?:https?://[a-z0-9\-]+\.internal)", re.IGNORECASE),
        re.compile(r"(?:https?://\d+\.\d+\.\d+\.\d+)", re.IGNORECASE),
    ]

    LDAP_INJECTION: list[re.Pattern] = [
        re.compile(r"(?:\*\)\s*\(\s*(?:objectclass|cn|uid|ou)\s*=)", re.IGNORECASE),
        re.compile(r"(?:\(\s*(?:objectclass|cn|uid|ou)\s*=\s*\*\s*\))", re.IGNORECASE),
        re.compile(r"(?:\)\s*\(\s*\(\s*\)\s*\))", re.IGNORECASE),
        re.compile(r"(?:\)\s*\|\s*\(\s*\))", re.IGNORECASE),
        re.compile(r"(?:\\2a|\\28|\\29|\\5c)", re.IGNORECASE),
        re.compile(r"(?:\(\s*\|\s*(?:uid|cn|ou)\s*=\s*)", re.IGNORECASE),
        re.compile(r"(?i)(?:objectclass\s*=\s*\*)", re.IGNORECASE),
    ]

    @classmethod
    def check(cls, text: str) -> list[dict]:
        """Return all matched attack categories with index details."""
        if not text:
            return []

        groups = {
            "sql_injection": cls.SQL_INJECTION,
            "xss": cls.XSS,
            "path_traversal": cls.PATH_TRAVERSAL,
            "command_injection": cls.COMMAND_INJECTION,
            "ssrf": cls.SSRF,
            "ldap_injection": cls.LDAP_INJECTION,
        }
        hits: list[dict] = []
        for name, patterns in groups.items():
            for idx, pat in enumerate(patterns):
                if pat.search(text):
                    hits.append({"attack_type": name, "pattern_index": idx})
        return hits


# ===================================================================
# RateLimiter  (token-bucket per IP)
# ===================================================================

class _TokenBucket:
    """Thread-safe token bucket for a single key."""

    __slots__ = ("capacity", "tokens", "refill_rate", "last_refill", "lock")

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.monotonic()
        self.lock = Lock()

    def consume(self, now: float | None = None) -> bool:
        """Try to consume one token. Returns True if allowed."""
        now = now or time.monotonic()
        with self.lock:
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

    def available(self) -> int:
        return int(self.tokens)


class RateLimiter:
    """Per-IP token-bucket rate limiter with endpoint overrides."""

    def __init__(self):
        self._lock = Lock()
        self._buckets: dict[str, _TokenBucket] = {}
        self._blocked: dict[str, float] = {}  # ip -> unblock_at

    def _get_or_create_bucket(self, key: str, capacity: int) -> _TokenBucket:
        with self._lock:
            if key not in self._buckets:
                refill_rate = capacity / WAFConfig.RATE_WINDOW
                self._buckets[key] = _TokenBucket(capacity, refill_rate)
            return self._buckets[key]

    def is_allowed(self, ip: str, endpoint: str | None = None) -> bool:
        """Check if the request is within rate limits."""
        # Check hard block
        if self._is_blocked(ip):
            return False

        # Endpoint-specific limit
        ep_limit = None
        if endpoint and endpoint in WAFConfig.RATE_LIMITS_PER_ENDPOINT:
            ep_limit = WAFConfig.RATE_LIMITS_PER_ENDPOINT[endpoint]

        if ep_limit is not None:
            bucket = self._get_or_create_bucket(f"ep:{ip}:{endpoint}", ep_limit)
            if not bucket.consume():
                self._on_rate_exceeded(ip, endpoint)
                return False

        # General IP limit
        bucket = self._get_or_create_bucket(f"ip:{ip}", WAFConfig.RATE_LIMIT)
        if not bucket.consume():
            self._on_rate_exceeded(ip, None)
            return False

        return True

    def block_ip(self, ip: str, duration: int | None = None) -> None:
        duration = duration or WAFConfig.BLOCK_DURATION
        with self._lock:
            self._blocked[ip] = time.monotonic() + duration
        logger.warning("IP %s blocked for %ds", ip, duration)

    def unblock_ip(self, ip: str) -> None:
        with self._lock:
            self._blocked.pop(ip, None)

    def is_ip_blocked(self, ip: str) -> bool:
        return self._is_blocked(ip)

    def _is_blocked(self, ip: str) -> bool:
        with self._lock:
            unblock_at = self._blocked.get(ip)
            if unblock_at is None:
                return False
            if time.monotonic() >= unblock_at:
                del self._blocked[ip]
                return False
            return True

    def _on_rate_exceeded(self, ip: str, endpoint: str | None) -> None:
        logger.warning("Rate limit exceeded for IP %s (endpoint=%s)", ip, endpoint)
        self.block_ip(ip)

    def cleanup(self) -> None:
        """Remove expired entries."""
        now = time.monotonic()
        with self._lock:
            expired = [ip for ip, t in self._blocked.items() if now >= t]
            for ip in expired:
                del self._blocked[ip]


# ===================================================================
# WAF Middleware
# ===================================================================

class WAFMiddleware(MiddlewareMixin):
    """
    Django middleware that performs WAF checks on every request.

    Priority order:
    1. Blocked IP check (instant reject)
    2. Body size validation
    3. Content-Type validation
    4. Request sanitization
    5. Attack pattern detection (URL, query, body, headers)
    6. Rate limiting
    7. Forward to view

    All blocked requests return HTTP 403 with a generic error message.
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        if not WAFConfig.ENABLED:
            return None

        ip = self._extract_ip(request)
        path = request.path

        # ---- 1. Blocked IP ----
        if self._is_blocked_ip(ip):
            self._log_block(
                "waf_blocked_ip", ThreatLevel.CRITICAL,
                ip, request, details={"path": path},
            )
            return self._block_response()

        # ---- 2. Body size ----
        try:
            content_length = int(request.META.get("CONTENT_LENGTH", 0) or 0)
        except (ValueError, TypeError):
            content_length = 0
        if content_length > WAFConfig.MAX_BODY_SIZE:
            self._log_block(
                "waf_oversized_payload", ThreatLevel.HIGH,
                ip, request,
                details={"path": path, "content_length": content_length, "max": WAFConfig.MAX_BODY_SIZE},
            )
            return self._block_response()

        # ---- 3. Content-Type ----
        content_type = request.META.get("CONTENT_TYPE", "")
        if request.method in ("POST", "PUT", "PATCH") and content_type:
            base_ct = content_type.split(";")[0].strip().lower()
            if base_ct not in WAFConfig.ALLOWED_CONTENT_TYPES:
                self._log_block(
                    "waf_invalid_content_type", ThreatLevel.LOW,
                    ip, request,
                    details={"path": path, "content_type": base_ct},
                )
                return self._block_response()

        # ---- 4. Sanitize & detect ----
        all_hits: list[dict] = []

        # URL
        all_hits.extend(AttackPatternDetector.check(path))

        # Query parameters
        if hasattr(request, "GET"):
            for key, val in request.GET.items():
                hits = AttackPatternDetector.check(f"{key}={val}")
                all_hits.extend(hits)

        # Body (only if readable)
        body_text = self._read_body(request)
        if body_text:
            all_hits.extend(AttackPatternDetector.check(body_text))
            # Also check decoded form data
            try:
                for pair in body_text.split("&"):
                    if "=" in pair:
                        all_hits.extend(AttackPatternDetector.check(pair))
            except Exception:
                pass

        # Headers
        for hdr in ("HTTP_REFERER", "HTTP_X_FORWARDED_FOR", "HTTP_COOKIE", "HTTP_USER_AGENT"):
            hdr_val = request.META.get(hdr, "")
            if hdr_val:
                all_hits.extend(AttackPatternDetector.check(hdr_val))

        if all_hits:
            threat_level = self._max_threat(all_hits)
            self._log_block(
                "waf_attack_detected", threat_level,
                ip, request,
                details={"path": path, "hits": all_hits[:20], "total_hits": len(all_hits)},
            )
            return self._block_response()

        # ---- 5. Rate limiting ----
        rate_limiter = RateLimiterSingleton.get()
        if not rate_limiter.is_allowed(ip, path):
            self._log_block(
                "waf_rate_limit_exceeded", ThreatLevel.MEDIUM,
                ip, request,
                details={"path": path, "limit": WAFConfig.RATE_LIMIT},
            )
            return self._block_response()

        # Passed all checks
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_ip(request: HttpRequest) -> str:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")

    @staticmethod
    def _is_blocked_ip(ip: str) -> bool:
        try:
            rec = BlockedIP.objects.get(ip_address=ip, is_active=True)
            if rec.is_expired():
                return False
            return True
        except BlockedIP.DoesNotExist:
            return False
        except Exception:
            return False

    @staticmethod
    def _read_body(request: HttpRequest) -> str:
        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode("utf-8", errors="replace")
            return body[:1_048_576]  # 1 MB cap
        except Exception:
            return ""

    @staticmethod
    def _max_threat(hits: list[dict]) -> int:
        levels = {
            "sql_injection": ThreatLevel.CRITICAL,
            "command_injection": ThreatLevel.CRITICAL,
            "path_traversal": ThreatLevel.HIGH,
            "xss": ThreatLevel.HIGH,
            "ssrf": ThreatLevel.HIGH,
            "ldap_injection": ThreatLevel.MEDIUM,
        }
        if not hits:
            return ThreatLevel.INFO
        return max(levels.get(h["attack_type"], ThreatLevel.LOW) for h in hits)

    @staticmethod
    def _block_response() -> HttpResponse:
        return JsonResponse(
            {"error": WAFConfig.BLOCK_RESPONSE_MESSAGE, "code": "WAF_BLOCKED"},
            status=403,
        )

    @staticmethod
    def _log_block(
        event_type: str,
        threat_level: int,
        ip: str,
        request: HttpRequest,
        details: dict | None = None,
    ) -> None:
        if not WAFConfig.LOG_BLOCKED:
            return
        user_id = ""
        if hasattr(request, "user") and request.user and request.user.is_authenticated:
            user_id = str(request.user.pk)
        try:
            SecurityEvent.objects.create(
                event_type=event_type,
                threat_level=threat_level,
                user_id=user_id,
                ip_address=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                endpoint=request.path,
                method=request.method,
                details=details or {},
                action_taken="blocked",
            )
        except Exception:
            logger.exception("Failed to persist WAF SecurityEvent")


# ===================================================================
# RateLimiter singleton (so middleware and WAFMiddleware share state)
# ===================================================================

class RateLimiterSingleton:
    _instance: RateLimiter | None = None
    _lock = Lock()

    @classmethod
    def get(cls) -> RateLimiter:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = RateLimiter()
        return cls._instance
