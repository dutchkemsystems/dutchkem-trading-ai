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
    Three target levels: Conservative (0.80%), Moderate (1.45%), Aggressive (2.20%)
    """

    TARGET_PROFILES = {
        "conservative": {
            "daily_target_pct": Decimal("0.80"),
            "description": "Conservative: 0.80% daily target",
        },
        "moderate": {
            "daily_target_pct": Decimal("1.45"),
            "description": "Moderate: 1.45% daily target",
        },
        "aggressive": {
            "daily_target_pct": Decimal("2.20"),
            "description": "Aggressive: 2.20% daily target",
        },
    }

    ALERT_THRESHOLD = Decimal("0.80")

    def __init__(self, profile: str = "moderate"):
        self.profile = profile
        self._target_pct = self.TARGET_PROFILES[profile]["daily_target_pct"]

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

        target_amount = starting_equity * (self._target_pct / 100)
        progress_pct = (daily_pnl / target_amount * 100) if target_amount > 0 else Decimal("0")

        is_target_reached = daily_pnl_pct >= self._target_pct
        is_alert_threshold = progress_pct >= (self.ALERT_THRESHOLD * 100)
        is_loss_limit = daily_pnl_pct <= -Decimal("2.0")

        is_trading_allowed = not is_target_reached and not is_loss_limit

        if monitor:
            monitor.is_daily_target_triggered = is_target_reached
            monitor.save(update_fields=["is_daily_target_triggered"])

        return {
            "date": today.isoformat(),
            "profile": self.profile,
            "daily_target_pct": str(self._target_pct),
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
