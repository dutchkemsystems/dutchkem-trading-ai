"""
Zero Trust Verification Engine for Dutchkem Trading AI.

Implements zero trust architecture with JWT validation, IP reputation checking,
device fingerprinting, micro-segmentation, and trust scoring.
"""

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import jwt
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("security")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRUST_THRESHOLD = 60
CACHE_TTL = 300  # 5 minutes for reputation caches
MAX_DEVICE_HISTORY = 10

KNOWN_TOR_EXIT_NODES = set()  # Populated from config or external feed

# Micro-segmentation trust requirements per path prefix
SEGMENT_TRUST_LEVELS = {
    "/api/v1/admin/": 90,
    "/api/v1/trading/execute/": 80,
    "/api/v1/trading/": 70,
    "/api/v1/payments/": 85,
    "/api/v1/accounts/": 60,
    "/api/v1/signals/": 60,
    "/api/v1/market-data/": 50,
    "/api/v1/analytics/": 50,
    "/api/v1/notifications/": 50,
}

DEFAULT_TRUST_LEVEL = 60


# ---------------------------------------------------------------------------
# Device Fingerprint
# ---------------------------------------------------------------------------
class DeviceFingerprint:
    """Generates and verifies device fingerprints from request headers."""

    @staticmethod
    def generate(user_agent: str, accept: str, tls_fingerprint: str = "") -> str:
        raw = f"{user_agent}|{accept}|{tls_fingerprint}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_from_request(request: HttpRequest) -> str:
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        accept = request.META.get("HTTP_ACCEPT", "")
        tls_fingerprint = request.META.get("HTTP_TLS_FINGERPRINT", "")
        return DeviceFingerprint.generate(user_agent, accept, tls_fingerprint)

    @staticmethod
    def verify(user_id: str, current_fp: str) -> bool:
        cache_key = f"device_fp:{user_id}"
        history: list[str] = cache.get(cache_key, [])

        if current_fp in history:
            return True

        if len(history) >= MAX_DEVICE_HISTORY:
            cache.delete(cache_key)
            return False

        history.append(current_fp)
        cache.set(cache_key, history, timeout=86400)
        return True


# ---------------------------------------------------------------------------
# IP Reputation Checker
# ---------------------------------------------------------------------------
class IPReputationChecker:
    """Checks IP addresses against reputation databases."""

    @staticmethod
    def is_blocked(ip_address: str) -> bool:
        from audit.models import AuditLog  # avoid circular import at module level

        cache_key = f"ip_blocked:{ip_address}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            from accounts.models import BlockedIP  # type: ignore[attr-defined]
            blocked = BlockedIP.objects.filter(
                ip_address=ip_address, is_active=True
            ).exists()
        except (ImportError, LookupError):
            blocked = False

        if blocked:
            cache.set(cache_key, True, timeout=CACHE_TTL)
            return True

        cache.set(cache_key, False, timeout=CACHE_TTL)
        return False

    @staticmethod
    def is_tor_exit(ip_address: str) -> bool:
        cache_key = f"ip_tor:{ip_address}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        is_tor = ip_address in KNOWN_TOR_EXIT_NODES
        cache.set(cache_key, is_tor, timeout=CACHE_TTL)
        return is_tor

    @staticmethod
    def get_reputation_score(ip_address: str) -> int:
        """Return 0-100 reputation score. 100 = clean, 0 = blocked."""
        if IPReputationChecker.is_blocked(ip_address):
            return 0
        if IPReputationChecker.is_tor_exit(ip_address):
            return 10
        return 100


# ---------------------------------------------------------------------------
# Trust Scorer
# ---------------------------------------------------------------------------
class TrustScorer:
    """
    Computes a 0-100 trust score from multiple signals.

    Scoring breakdown:
      - JWT validity:         20 points
      - IP reputation:        25 points
      - Device fingerprint:   20 points
      - Time anomalies:       15 points
      - Behavioral patterns:  20 points
    """

    @staticmethod
    def compute(
        jwt_valid: bool,
        jwt_claims: dict[str, Any],
        ip_reputation: int,
        device_match: bool,
        request: HttpRequest,
        user_id: Optional[str] = None,
    ) -> tuple[int, dict[str, Any]]:
        breakdown: dict[str, Any] = {}

        # --- JWT Validity (20 pts) ---
        jwt_score = 20 if jwt_valid else 0
        breakdown["jwt"] = jwt_score

        # --- IP Reputation (25 pts) ---
        ip_score = round(ip_reputation * 25 / 100)
        breakdown["ip_reputation"] = ip_score

        # --- Device Fingerprint (20 pts) ---
        device_score = 20 if device_match else 0
        breakdown["device"] = device_score

        # --- Time-based Anomalies (15 pts) ---
        time_score = TrustScorer._time_anomaly_score(jwt_claims)
        breakdown["time"] = time_score

        # --- Behavioral Patterns (20 pts) ---
        behavioral_score = TrustScorer._behavioral_score(request, user_id)
        breakdown["behavioral"] = behavioral_score

        total = jwt_score + ip_score + device_score + time_score + behavioral_score
        return total, breakdown

    @staticmethod
    def _time_anomaly_score(claims: dict[str, Any]) -> int:
        """Penalise tokens issued outside normal business hours or with short TTLs."""
        try:
            issued_at = claims.get("iat", 0)
            now = time.time()
            age = now - issued_at

            hour = datetime.fromtimestamp(issued_at, tz=timezone.utc).hour
            if 0 <= hour <= 5:
                return 5  # suspicious hour
            if age > 3600 * 8:
                return 8  # very old token
            return 15
        except Exception:
            return 10

    @staticmethod
    def _behavioral_score(request: HttpRequest, user_id: Optional[str]) -> int:
        """Simple velocity check – many requests in short window → lower trust."""
        if not user_id:
            return 15

        cache_key = f"behavior:{user_id}"
        request_times: list[float] = cache.get(cache_key, [])
        now = time.time()

        request_times = [t for t in request_times if now - t < 60]
        request_times.append(now)
        cache.set(cache_key, request_times, timeout=120)

        if len(request_times) > 100:
            return 5
        if len(request_times) > 50:
            return 10
        return 20


# ---------------------------------------------------------------------------
# Zero Trust Middleware
# ---------------------------------------------------------------------------
class ZeroTrustMiddleware(MiddlewareMixin):
    """
    Django middleware implementing zero trust verification.

    Validates JWT claims, checks IP reputation, verifies device fingerprints,
    applies micro-segmentation trust thresholds, and logs all events.
    """

    # Paths that bypass zero-trust checks
    EXEMPT_PATHS = {
        "/api/v1/auth/token/",
        "/api/v1/auth/token/refresh/",
        "/admin/",
        "/health/",
        "/metrics/",
    }

    def process_request(self, request: HttpRequest) -> Optional[JsonResponse]:
        if request.path in self.EXEMPT_PATHS:
            return None

        if not request.path.startswith("/api/"):
            return None

        # --- Extract token ---
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return self._deny(request, "missing_token", "No Bearer token provided")

        token = auth_header.split(" ", 1)[1]

        # --- Validate JWT ---
        jwt_claims = self._validate_jwt(token)
        if jwt_claims is None:
            return self._deny(request, "invalid_token", "JWT validation failed")

        user_id = str(jwt_claims.get("user_id", ""))

        # --- IP reputation ---
        client_ip = self._get_client_ip(request)
        ip_reputation = IPReputationChecker.get_reputation_score(client_ip)

        # --- Device fingerprint ---
        current_fp = DeviceFingerprint.generate_from_request(request)
        device_match = DeviceFingerprint.verify(user_id, current_fp)

        # --- Compute trust score ---
        trust_score, breakdown = TrustScorer.compute(
            jwt_valid=True,
            jwt_claims=jwt_claims,
            ip_reputation=ip_reputation,
            device_match=device_match,
            request=request,
            user_id=user_id,
        )

        # --- Micro-segmentation ---
        required_trust = self._required_trust_level(request.path)

        # --- Log verification event ---
        self._log_event(
            request=request,
            user_id=user_id,
            trust_score=trust_score,
            breakdown=breakdown,
            ip_address=client_ip,
            device_fingerprint=current_fp,
            allowed=trust_score >= required_trust,
        )

        if trust_score < required_trust:
            return self._deny(
                request,
                "insufficient_trust",
                f"Trust score {trust_score} below required {required_trust}",
                extra={"trust_score": trust_score, "required": required_trust, "breakdown": breakdown},
            )

        # Attach trust context to request for downstream use
        request.zt_trust_score = trust_score
        request.zt_breakdown = breakdown
        request.zt_user_id = user_id

        return None

    # -- Helpers -----------------------------------------------------------

    def _validate_jwt(self, token: str) -> Optional[dict[str, Any]]:
        try:
            signing_key = getattr(settings, "SIMPLE_JWT", {}).get("SIGNING_KEY", settings.SECRET_KEY)
            algorithm = getattr(settings, "SIMPLE_JWT", {}).get("ALGORITHM", "HS256")

            claims = jwt.decode(
                token,
                signing_key,
                algorithms=[algorithm],
                options={
                    "require": ["exp", "iss", "aud", "jti"],
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
                issuer=getattr(settings, "JWT_ISSUER", "dutchkem-trading"),
                audience=getattr(settings, "JWT_AUDIENCE", "dutchkem-api"),
            )

            # Check token revocation via cache
            jti = claims.get("jti", "")
            if cache.get(f"revoked_token:{jti}"):
                logger.warning("Revoked token used: jti=%s", jti)
                return None

            return claims
        except jwt.ExpiredSignatureError:
            logger.info("Expired JWT presented")
            return None
        except jwt.InvalidAudienceError:
            logger.warning("Invalid audience in JWT")
            return None
        except jwt.InvalidIssuerError:
            logger.warning("Invalid issuer in JWT")
            return None
        except jwt.MissingRequiredClaimError as exc:
            logger.warning("Missing required claim: %s", exc)
            return None
        except jwt.DecodeError:
            logger.warning("JWT decode error")
            return None
        except Exception as exc:
            logger.error("Unexpected JWT validation error: %s", exc)
            return None

    def _get_client_ip(self, request: HttpRequest) -> str:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")

    def _required_trust_level(self, path: str) -> int:
        for prefix, level in sorted(SEGMENT_TRUST_LEVELS.items(), key=lambda x: -len(x[0])):
            if path.startswith(prefix):
                return level
        return DEFAULT_TRUST_LEVEL

    def _log_event(
        self,
        request: HttpRequest,
        user_id: str,
        trust_score: int,
        breakdown: dict[str, Any],
        ip_address: str,
        device_fingerprint: str,
        allowed: bool,
    ) -> None:
        try:
            from audit.models import AuditLog

            AuditLog.objects.create(
                user_id=user_id if user_id else None,
                action="zero_trust_check",
                resource_type="security",
                resource_id=request.path,
                changes={
                    "trust_score": trust_score,
                    "breakdown": breakdown,
                    "ip_address": ip_address,
                    "device_fingerprint": device_fingerprint[:16],
                    "method": request.method,
                    "allowed": allowed,
                },
                severity="WARNING" if not allowed else "INFO",
                ip_address=ip_address,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            )
        except Exception as exc:
            logger.error("Failed to log zero trust event: %s", exc)

    def _deny(
        self,
        request: HttpRequest,
        reason_code: str,
        message: str,
        extra: Optional[dict[str, Any]] = None,
    ) -> JsonResponse:
        client_ip = self._get_client_ip(request)
        logger.warning(
            "ZeroTrust DENY reason=%s path=%s ip=%s message=%s",
            reason_code,
            request.path,
            client_ip,
            message,
        )

        try:
            from audit.models import AuditLog

            AuditLog.objects.create(
                action="zero_trust_denied",
                resource_type="security",
                resource_id=request.path,
                changes={
                    "reason_code": reason_code,
                    "message": message,
                    "ip_address": client_ip,
                    "method": request.method,
                    **(extra or {}),
                },
                severity="WARNING",
                ip_address=client_ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            )
        except Exception as exc:
            logger.error("Failed to log zero trust deny event: %s", exc)

        body = {"error": "Forbidden", "reason": reason_code, "message": message}
        return JsonResponse(body, status=403)
