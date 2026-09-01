"""
V6.5 Backup System Manager
Manages fallback trading systems when V6.5 encounters issues.

Fallback Priority Chain:
  1. V6.5 Ultimate Enhanced (PRIMARY)
  2. V6 Orchestrator (PRIMARY FALLBACK)
  3. Gold Edge (XAUUSD Specialist)
  4. Scalping (M5/M15 Tight Trades)
  5. Confluence Engine (Multi-TF)

Each backup system activates when:
  - V6.5 fails to initialize
  - V6.5 component health drops below threshold
  - V6.5 encounters errors during cycle execution
  - Market regime matches backup specialty (e.g., Gold Edge for XAUUSD)
"""

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ml.backup_manager")


class BackupSystem(str, Enum):
    V65 = "V6.5_ORCHESTRATOR"
    V6 = "V6_ORCHESTRATOR"
    GOLD_EDGE = "GOLD_EDGE"
    SCALPING = "SCALPING"
    CONFLUENCE = "CONFLUENCE_ENGINE"


class BackupTrigger(str, Enum):
    V65_INIT_FAILURE = "V65_INIT_FAILURE"
    V65_COMPONENT_DEGRADED = "V65_COMPONENT_DEGRADED"
    V65_CYCLE_ERROR = "V65_CYCLE_ERROR"
    XAUUSD_SPECIALIST = "XAUUSD_SPECIALIST"
    M5_SCALPING_OPPORTUNITY = "M5_SCALPING_OPPORTUNITY"
    MULTI_TF_ALIGNMENT = "MULTI_TF_ALIGNMENT"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


# Fallback priority chain
FALLBACK_CHAIN: List[BackupSystem] = [
    BackupSystem.V65,
    BackupSystem.V6,
    BackupSystem.GOLD_EDGE,
    BackupSystem.SCALPING,
    BackupSystem.CONFLUENCE,
]

# XAUUSD-specific symbols that trigger Gold Edge
GOLD_EDGE_SYMBOLS = {"XAUUSD", "XAGUSD", "XAUEUR"}

# Scalping-eligible timeframes
SCALPING_TIMEFRAMES = {"M5", "M15"}

# Component health threshold — if V6.5 drops below this, activate backup
MIN_COMPONENT_HEALTH_PCT = 50.0


class BackupManager:
    """
    Manages which trading system is active and handles fallback logic.

    The BackupManager monitors V6.5 health and automatically activates
    backup systems when needed. It logs all system switches for audit.
    """

    def __init__(self):
        self.current_system = BackupSystem.V65
        self.previous_system: Optional[BackupSystem] = None
        self.activation_log: List[Dict[str, Any]] = []
        self._v65_failures = 0
        self._max_v65_failures = 3  # After 3 consecutive failures, switch to backup
        self._last_switch_time: Optional[datetime] = None
        self._cooldown_seconds = 300  # 5 minutes before switching back to V6.5

    def get_active_system(self) -> BackupSystem:
        """Get the currently active trading system."""
        return self.current_system

    def should_activate_backup(
        self,
        v65_health_pct: float = 100.0,
        cycle_error: Optional[str] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> bool:
        """
        Determine if a backup system should be activated.

        Args:
            v65_health_pct: V6.5 component health percentage (0-100)
            cycle_error: Error message from V6.5 cycle execution
            symbol: Current symbol being analyzed
            timeframe: Current timeframe being analyzed

        Returns:
            True if backup should be activated
        """
        # Check 1: V6.5 component health
        if v65_health_pct < MIN_COMPONENT_HEALTH_PCT:
            logger.warning(
                "V6.5 health %.1f%% below threshold %.1f%% — activating backup",
                v65_health_pct,
                MIN_COMPONENT_HEALTH_PCT,
            )
            self._log_activation(
                BackupTrigger.V65_COMPONENT_DEGRADED,
                f"Health: {v65_health_pct:.1f}%",
            )
            return True

        # Check 2: V6.5 cycle error
        if cycle_error:
            self._v65_failures += 1
            logger.warning(
                "V6.5 cycle error (%d/%d): %s",
                self._v65_failures,
                self._max_v65_failures,
                cycle_error,
            )
            if self._v65_failures >= self._max_v65_failures:
                self._log_activation(
                    BackupTrigger.V65_CYCLE_ERROR,
                    f"Consecutive failures: {self._v65_failures}",
                )
                return True

        # Check 3: Symbol-specific specialists
        if symbol and symbol in GOLD_EDGE_SYMBOLS:
            if self.current_system != BackupSystem.GOLD_EDGE:
                logger.info(
                    "Symbol %s matches Gold Edge specialty — considering activation",
                    symbol,
                )
                # Only activate Gold Edge if V6.5 is degraded
                if v65_health_pct < 80.0:
                    self._log_activation(
                        BackupTrigger.XAUUSD_SPECIALIST,
                        f"Symbol: {symbol}",
                    )
                    return True

        # Check 4: Scalping opportunity on M5/M15
        if timeframe in SCALPING_TIMEFRAMES and v65_health_pct < 70.0:
            self._log_activation(
                BackupTrigger.M5_SCALPING_OPPORTUNITY,
                f"Timeframe: {timeframe}, Health: {v65_health_pct:.1f}%",
            )
            return True

        return False

    def activate_backup(self, trigger: BackupTrigger, reason: str) -> BackupSystem:
        """
        Activate the next backup system in the priority chain.

        Returns:
            The newly activated backup system
        """
        current_idx = FALLBACK_CHAIN.index(self.current_system)

        # Try the next system in the chain
        for idx in range(current_idx + 1, len(FALLBACK_CHAIN)):
            backup = FALLBACK_CHAIN[idx]
            logger.info(
                "Activating backup system: %s (trigger: %s, reason: %s)",
                backup.value,
                trigger.value,
                reason,
            )
            self.previous_system = self.current_system
            self.current_system = backup
            self._last_switch_time = datetime.now()
            self._log_activation(trigger, reason, switched_to=backup)
            return backup

        # If all backups exhausted, stay on current
        logger.error("All backup systems exhausted — staying on %s", self.current_system.value)
        return self.current_system

    def check_v65_recovery(self) -> bool:
        """
        Check if V6.5 has recovered and should be reactivated.

        Returns:
            True if V6.5 should be reactivated
        """
        if self.current_system == BackupSystem.V65:
            return False  # Already on V6.5

        # Cooldown check
        if self._last_switch_time:
            elapsed = (datetime.now() - self._last_switch_time).total_seconds()
            if elapsed < self._cooldown_seconds:
                return False

        # Check if V6.5 failures have reset
        if self._v65_failures == 0:
            logger.info("V6.5 recovery detected — switching back to primary")
            self.previous_system = self.current_system
            self.current_system = BackupSystem.V65
            self._log_activation(
                BackupTrigger.MANUAL_OVERRIDE,
                "V6.5 recovered",
                switched_to=BackupSystem.V65,
            )
            return True

        return False

    def reset_v65_failures(self):
        """Reset V6.5 failure counter (call after successful V6.5 cycle)."""
        self._v65_failures = 0

    def get_system_for_symbol(self, symbol: str) -> BackupSystem:
        """
        Get the best system for a given symbol.

        For XAUUSD/XAGUSD, prefer Gold Edge.
        For everything else, use the current active system.
        """
        if symbol in GOLD_EDGE_SYMBOLS and self.current_system == BackupSystem.V65:
            return BackupSystem.GOLD_EDGE
        return self.current_system

    def _log_activation(
        self,
        trigger: BackupTrigger,
        reason: str,
        switched_to: Optional[BackupSystem] = None,
    ):
        """Log a backup activation event."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trigger": trigger.value,
            "reason": reason,
            "from_system": self.current_system.value,
            "to_system": (switched_to or self.current_system).value,
        }
        self.activation_log.append(entry)
        logger.info(
            "Backup activation logged: %s -> %s (trigger: %s)",
            entry["from_system"],
            entry["to_system"],
            trigger.value,
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current backup manager status."""
        return {
            "current_system": self.current_system.value,
            "previous_system": self.previous_system.value if self.previous_system else None,
            "v65_failures": self._v65_failures,
            "max_v65_failures": self._max_v65_failures,
            "total_activations": len(self.activation_log),
            "recent_activations": self.activation_log[-5:] if self.activation_log else [],
            "fallback_chain": [s.value for s in FALLBACK_CHAIN],
        }

    def get_activation_history(self) -> List[Dict[str, Any]]:
        """Get full activation log for audit."""
        return self.activation_log.copy()


# ── Singleton accessor ──────────────────────────────────────────────
_backup_manager: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    """Get or create the singleton BackupManager instance."""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager
