"""
Security Facade — Unified entry point for all security subsystems.

Lazy-loads zero_trust, waf, ids, siem, rasp, fips_encryption, and
encryption. Provides a single ``verify_request`` method that runs all
checks, with each check isolated by try/except so one failure never
blocks others.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("security.facade")


class SecurityLayer:
    """
    Facade over all security components.

    Components are lazy-loaded on first access.  Each subsystem check is
    independently wrapped in a try/except so that failures in one layer
    do not cascade.
    """

    def __init__(self):
        self.zero_trust = None
        self.waf = None
        self.ids = None
        self.siem = None
        self.rasp = None
        self.fips_encryption = None
        self.encryption = None

        self._component_health: Dict[str, bool] = {}
        self._initialized = False

    # ── Lazy loader ─────────────────────────────────────────────────

    def _lazy_load(self, module_path: str, attr_name: str, friendly_name: str):
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, attr_name)
            instance = cls()
            logger.info("SecurityLayer loaded: %s", friendly_name)
            self._component_health[friendly_name] = True
            return instance
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("SecurityLayer optional component not installed: %s (%s)", friendly_name, e)
            self._component_health[friendly_name] = False
            return None
        except AttributeError as e:
            logger.error("SecurityLayer component class missing: %s (%s)", friendly_name, e)
            self._component_health[friendly_name] = False
            return None
        except Exception as e:
            logger.error("SecurityLayer component failed to initialise: %s (%s)", friendly_name, e, exc_info=True)
            self._component_health[friendly_name] = False
            return None

    def initialize(self):
        """Lazy-load all security components."""
        if self._initialized:
            return

        self.zero_trust = self._lazy_load(
            "security.zero_trust", "ZeroTrustMiddleware", "ZeroTrust",
        )
        self.waf = self._lazy_load(
            "security.waf", "WAFMiddleware", "WAF",
        )
        self.ids = self._lazy_load(
            "security.intrusion_detection", "IntrusionDetectionSystem", "IDS",
        )
        self.siem = self._lazy_load(
            "security.siem", "SIEMEngine", "SIEM",
        )
        self.rasp = self._lazy_load(
            "security.rasp", "RASPEngine", "RASP",
        )
        self.fips_encryption = self._lazy_load(
            "security.fips_encryption", "FIPSEncryption", "FIPSEncryption",
        )
        self.encryption = self._lazy_load(
            "security.encryption", "EncryptionService", "Encryption",
        )

        self._initialized = True
        loaded = sum(1 for v in self._component_health.values() if v)
        logger.info("SecurityLayer initialised — %d/7 components loaded", loaded)

    # ── Verify request ──────────────────────────────────────────────

    def verify_request(self, request: Any) -> Dict[str, Any]:
        """
        Run all security checks against an incoming request.

        Returns::

            {
                "allowed": bool,
                "checks": { "component_name": { "passed": bool, "details": ... } },
                "timestamp": str,
            }
        """
        self.initialize()
        timestamp = datetime.now(timezone.utc).isoformat()
        checks: Dict[str, Dict[str, Any]] = {}
        overall_allowed = True

        # 1. WAF check
        if self.waf:
            try:
                waf_result = self.waf.process_request(request)
                blocked = waf_result is not None
                checks["waf"] = {"passed": not blocked, "details": "blocked" if blocked else "ok"}
                if blocked:
                    overall_allowed = False
            except Exception as e:
                logger.error("WAF check failed: %s", e)
                checks["waf"] = {"passed": True, "details": f"error: {e}"}
        else:
            checks["waf"] = {"passed": True, "details": "not_available"}

        # 2. Zero Trust check
        if self.zero_trust:
            try:
                zt_result = self.zero_trust.process_request(request)
                blocked = zt_result is not None
                checks["zero_trust"] = {"passed": not blocked, "details": "denied" if blocked else "ok"}
                if blocked:
                    overall_allowed = False
            except Exception as e:
                logger.error("Zero Trust check failed: %s", e)
                checks["zero_trust"] = {"passed": True, "details": f"error: {e}"}
        else:
            checks["zero_trust"] = {"passed": True, "details": "not_available"}

        # 3. IDS check
        if self.ids:
            try:
                threat_level, ids_result = self.ids.analyze_request(request)
                blocked = ids_result.get("blocked", False)
                checks["ids"] = {
                    "passed": not blocked,
                    "details": {"threat_level": threat_level, "reasons": ids_result.get("reasons", [])},
                }
                if blocked:
                    overall_allowed = False
            except Exception as e:
                logger.error("IDS check failed: %s", e)
                checks["ids"] = {"passed": True, "details": f"error: {e}"}
        else:
            checks["ids"] = {"passed": True, "details": "not_available"}

        # 4. RASP check (integrity / tamper)
        if self.rasp:
            try:
                rasp_status = self.rasp.get_protection_status()
                checks["rasp"] = {"passed": True, "details": rasp_status}
            except Exception as e:
                logger.error("RASP check failed: %s", e)
                checks["rasp"] = {"passed": True, "details": f"error: {e}"}
        else:
            checks["rasp"] = {"passed": True, "details": "not_available"}

        return {
            "allowed": overall_allowed,
            "checks": checks,
            "timestamp": timestamp,
        }

    # ── Data encryption helpers ─────────────────────────────────────

    def encrypt_sensitive_data(self, data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """
        Encrypt specified fields in *data* using FIPSEncryption.

        Returns a new dict with encrypted values replacing originals.
        """
        self.initialize()
        result = dict(data)

        if not self.fips_encryption:
            logger.warning("FIPSEncryption not available — skipping encryption")
            return result

        for field_name in fields:
            if field_name in result and result[field_name] is not None:
                try:
                    encrypted = self.fips_encryption.encrypt_field(result[field_name], field_name)
                    result[field_name] = encrypted
                except Exception as e:
                    logger.error("Failed to encrypt field '%s': %s", field_name, e)

        return result

    # ── SIEM logging ────────────────────────────────────────────────

    def log_security_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        Log a security event to the SIEM subsystem.

        Non-fatal — errors are swallowed so logging never blocks the caller.
        """
        self.initialize()
        if not self.siem:
            logger.debug("SIEM not available — event '%s' not logged", event_type)
            return

        try:
            self.siem.process_event(
                event_type=event_type,
                details=details,
                user_id=details.get("user_id", ""),
                ip_address=details.get("ip_address"),
            )
        except Exception as e:
            logger.error("SIEM event logging failed: %s", e)

    # ── Health ──────────────────────────────────────────────────────

    def get_security_status(self) -> Dict[str, Any]:
        """Return health of all security components."""
        self.initialize()
        return {
            "initialized": self._initialized,
            "component_health": self._component_health.copy(),
            "components_loaded": sum(1 for v in self._component_health.values() if v),
            "total_components": 7,
        }
