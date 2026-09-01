import logging
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("risk_management.daily_target")


class DailyTargetLock:
    """
    Daily target tracking and enforcement system.

    V6.5 COMPULSORY: This class now DEFERS to V6.5's ProfitTargetManager
    for all target determination. The hardcoded profiles below serve only
    as fallback values when V6.5 is unavailable.

    Target hierarchy:
      1. V6.5 ProfitTargetManager (COMPULSORY — dynamic, performance-based)
      2. Fallback profiles (only when V6.5 is not available)
    """

    # Fallback profiles — used ONLY when V6.5 is unavailable
    TARGET_PROFILES = {
        "conservative": {
            "daily_target_pct": Decimal("0.80"),
            "description": "V6.5 fallback Conservative profile",
        },
        "moderate": {
            "daily_target_pct": Decimal("1.45"),
            "description": "V6.5 fallback Moderate profile",
        },
        "aggressive": {
            "daily_target_pct": Decimal("2.20"),
            "description": "V6.5 fallback Aggressive profile",
        },
    }

    ALERT_THRESHOLD = Decimal("0.80")

    def __init__(self, profile: str = "moderate"):
        self.profile = profile
        self._target_pct = self.TARGET_PROFILES[profile]["daily_target_pct"]
        self._v65_active = False

    def _get_v65_daily_target(self, user=None) -> Optional[Decimal]:
        """
        Attempt to get the daily target from V6.5's ProfitTargetManager.
        Returns None if V6.5 is not available.
        """
        try:
            from ml.enhancements.profit_target_manager import ProfitTargetManager
            manager = ProfitTargetManager()

            # Get account data
            current_equity = float(user.equity) if user and hasattr(user, 'equity') else 10000.0
            peak_equity = current_equity

            try:
                from risk_management.models import DrawdownMonitor
                monitor = DrawdownMonitor.objects.filter(user=user).first() if user else None
                if monitor:
                    peak_equity = float(monitor.peak_equity)
            except Exception:
                pass

            # Get recent trades
            recent_trades = []
            try:
                from trading.models import Trade
                recent = Trade.objects.filter(status="CLOSED").order_by("-closed_at")[:50]
                recent_trades = [{"pnl": float(t.profit_loss or 0)} for t in recent]
            except Exception:
                pass

            # Compute V6.5 targets
            targets = manager.compute_targets(
                current_equity=current_equity,
                peak_equity=peak_equity,
                recent_trades=recent_trades,
                regime="NORMAL",
            )

            daily_pct = targets.get("targets", {}).get("daily_pct")
            if daily_pct is not None:
                self._v65_active = True
                logger.info(
                    "DailyTargetLock: Using V6.5 dynamic target %.4f%% (was %.2f%%)",
                    daily_pct, float(self._target_pct),
                )
                return Decimal(str(daily_pct))

        except Exception as e:
            logger.debug("V6.5 ProfitTargetManager unavailable for DailyTargetLock: %s", e)

        return None

    @property
    def daily_target_pct(self) -> Decimal:
        return self._target_pct

    def check_daily_status(self, user) -> Dict[str, Any]:
        from risk_management.models import DailyPerformance, DrawdownMonitor

        today = timezone.now().date()
        performance = DailyPerformance.objects.filter(
            user=user, date=today
        ).first()

        monitor = DrawdownMonitor.objects.filter(user=user).first()

        starting_equity = (
            performance.starting_equity if performance
            else (monitor.current_equity if monitor else user.equity)
        )

        current_equity = user.equity
        daily_pnl = current_equity - starting_equity
        daily_pnl_pct = (daily_pnl / starting_equity * 100) if starting_equity > 0 else Decimal("0")

        # ── V6.5 COMPULSORY: Use V6.5 target if available ────────────
        v65_target = self._get_v65_daily_target(user)
        if v65_target is not None:
            effective_target = v65_target
            source = "V6.5_ORCHESTRATOR"
        else:
            effective_target = self._target_pct
            source = "FALLBACK_PROFILE"

        target_amount = starting_equity * (effective_target / 100)
        progress_pct = (daily_pnl / target_amount * 100) if target_amount > 0 else Decimal("0")

        is_target_reached = daily_pnl_pct >= effective_target
        is_alert_threshold = progress_pct >= (self.ALERT_THRESHOLD * 100)
        is_loss_limit = daily_pnl_pct <= -Decimal("2.0")

        is_trading_allowed = not is_target_reached and not is_loss_limit

        if monitor:
            monitor.is_daily_target_triggered = is_target_reached
            monitor.save(update_fields=["is_daily_target_triggered"])

        return {
            "date": today.isoformat(),
            "profile": self.profile,
            "source": source,
            "daily_target_pct": str(effective_target),
            "v65_active": self._v65_active,
            "starting_equity": str(starting_equity),
            "current_equity": str(current_equity),
            "daily_pnl": str(daily_pnl),
            "daily_pnl_pct": str(round(daily_pnl_pct, 4)),
            "target_amount": str(target_amount),
            "progress_pct": str(round(progress_pct, 2)),
            "is_target_reached": is_target_reached,
            "is_alert_threshold": is_alert_threshold,
            "is_loss_limit": is_loss_limit,
            "is_trading_allowed": is_trading_allowed,
            "remaining_to_target": str(target_amount - daily_pnl) if daily_pnl < target_amount else "0",
        }

    @transaction.atomic
    def enforce_daily_target(self, user) -> Dict[str, Any]:
        status = self.check_daily_status(user)

        if not status["is_trading_allowed"]:
            if status["is_target_reached"]:
                self._close_profitable_positions(user)
                self._create_alert(
                    user,
                    "DAILY_TARGET",
                    "INFO",
                    f"Daily target {self._target_pct}% reached. Trading halted. P&L: {status['daily_pnl_pct']}%",
                )
                return {
                    "action": "halt",
                    "reason": "daily_target_reached",
                    "status": status,
                }

            if status["is_loss_limit"]:
                self._close_all_positions(user)
                self._create_alert(
                    user,
                    "DAILY_LOSS",
                    "CRITICAL",
                    f"Daily loss limit 2% reached. All positions closed. P&L: {status['daily_pnl_pct']}%",
                )
                return {
                    "action": "halt_close_all",
                    "reason": "daily_loss_limit",
                    "status": status,
                }

        if status["is_alert_threshold"] and not status["is_target_reached"]:
            self._create_alert(
                user,
                "DAILY_TARGET",
                "HIGH",
                f"Daily target 80% achieved. Progress: {status['progress_pct']}%",
            )

        return {
            "action": "continue",
            "status": status,
        }

    def _close_profitable_positions(self, user):
        from trading.models import Position, Trade
        from trading.services import order_service

        positions = Position.objects.filter(user=user)
        for position in positions:
            try:
                if position.unrealized_pnl > 0:
                    order_service.close_trade(
                        trade_id=str(position.trade_id),
                        user=user,
                    )
                    logger.info("Closed profitable position: %s %s", position.symbol.name, position.position_type)
            except Exception as e:
                logger.error("Error closing position: %s", e)

    def _close_all_positions(self, user):
        from trading.models import Position
        from trading.services import order_service

        positions = Position.objects.filter(user=user)
        for position in positions:
            try:
                order_service.close_trade(
                    trade_id=str(position.trade_id),
                    user=user,
                )
                logger.info("Closed position: %s %s", position.symbol.name, position.position_type)
            except Exception as e:
                logger.error("Error closing position: %s", e)

    def _create_alert(self, user, alert_type: str, severity: str, message: str):
        from risk_management.models import RiskAlert

        RiskAlert.objects.create(
            user=user,
            alert_type=alert_type,
            severity=severity,
            message=message,
            data={"profile": self.profile, "target_pct": str(self._target_pct)},
        )

    def override_halt(self, user, reason: str = "manual_override") -> Dict[str, Any]:
        from risk_management.models import DrawdownMonitor

        monitor = DrawdownMonitor.objects.filter(user=user).first()
        if monitor:
            monitor.is_daily_target_triggered = False
            monitor.is_circuit_breaker_triggered = False
            monitor.save(update_fields=[
                "is_daily_target_triggered",
                "is_circuit_breaker_triggered",
            ])

        self._create_alert(
            user,
            "OVERRIDE",
            "HIGH",
            f"Daily target halt overridden. Reason: {reason}",
        )

        logger.warning("Daily target halt overridden for user %s: %s", user.id, reason)

        return {
            "action": "override",
            "reason": reason,
            "trading_resumed": True,
        }

    @staticmethod
    def get_profile_for_risk_level(risk_level: str) -> str:
        mapping = {
            "low": "conservative",
            "medium": "moderate",
            "high": "aggressive",
            "conservative": "conservative",
            "moderate": "moderate",
            "aggressive": "aggressive",
        }
        return mapping.get(risk_level, "moderate")
