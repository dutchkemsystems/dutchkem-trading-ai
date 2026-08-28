import logging
import time
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("trading")


class OrderExecutionError(Exception):
    pass


class RiskCheckError(OrderExecutionError):
    pass


class InsufficientMarginError(OrderExecutionError):
    pass


class OrderExecutionService:
    """
    Complete order execution pipeline.
    Validates, executes, and tracks orders through MT5.
    """

    def __init__(self):
        self._mt5_service = None

    @property
    def mt5(self):
        if self._mt5_service is None:
            from mcp_integration.services import mt5_service
            self._mt5_service = mt5_service
        return self._mt5_service

    def validate_order(
        self,
        user,
        symbol,
        position_type: str,
        volume: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        order_type: str = "MARKET",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        from risk_management.models import DrawdownMonitor, RiskParameter

        risk_params = RiskParameter.objects.filter(is_active=True).first()
        if not risk_params:
            return False, "No active risk parameters", {}

        monitor = DrawdownMonitor.objects.filter(user=user).first()
        checks = {
            "daily_loss_ok": True,
            "drawdown_ok": True,
            "daily_trades_ok": True,
            "position_size_ok": True,
            "daily_target_ok": True,
        }

        if monitor:
            if monitor.is_circuit_breaker_triggered:
                return False, "Circuit breaker triggered", checks

            if monitor.is_daily_loss_triggered:
                checks["daily_loss_ok"] = False
                return False, "Daily loss limit reached", checks

            if monitor.is_drawdown_triggered:
                checks["drawdown_ok"] = False
                return False, "Max drawdown reached", checks

            if monitor.is_max_trades_triggered:
                checks["daily_trades_ok"] = False
                return False, "Max daily trades reached", checks

            if monitor.is_daily_target_triggered:
                checks["daily_target_ok"] = False
                return False, "Daily target reached", checks

            daily_trades = monitor.daily_trades_count
            if daily_trades >= risk_params.max_daily_trades:
                checks["daily_trades_ok"] = False
                return False, f"Max daily trades ({risk_params.max_daily_trades}) reached", checks

        equity = float(user.equity) if hasattr(user, "equity") else 10000.0
        risk_pct = float(risk_params.max_position_size)
        max_risk_amount = equity * (risk_pct / 100)
        volume_f = float(volume)
        if volume_f * 100000 > max_risk_amount * 20:
            checks["position_size_ok"] = False
            return False, "Position size exceeds risk limit", checks

        return True, "All checks passed", checks

    @transaction.atomic
    def execute_market_order(
        self,
        user,
        symbol,
        position_type: str,
        volume: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        magic: int = 123456,
        signal=None,
        expert_advisor=None,
    ) -> Dict[str, Any]:
        from trading.models import Order, Position, Symbol, Trade

        valid, message, checks = self.validate_order(
            user, symbol, position_type, volume, stop_loss, take_profit
        )
        if not valid:
            raise RiskCheckError(message)

        sym = Symbol.objects.get(id=symbol) if isinstance(symbol, str) else symbol

        order = Order.objects.create(
            user=user,
            symbol=sym,
            order_type="MARKET",
            position_type=position_type,
            volume=volume,
            price=Decimal("0"),
            stop_loss=stop_loss,
            take_profit=take_profit,
            status="PENDING",
            signal=signal,
        )

        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                self.mt5.open_position(
                    symbol=sym.name,
                    volume=float(volume),
                    position_type=position_type,
                    stop_loss=float(stop_loss) if stop_loss else 0.0,
                    take_profit=float(take_profit) if take_profit else 0.0,
                    magic=magic,
                )
            )
        finally:
            loop.close()

        if not result.get("success"):
            order.status = "REJECTED"
            order.save()
            raise OrderExecutionError(
                f"MT5 order failed: {result.get('error', 'Unknown error')}"
            )

        mt5_data = result.get("data", {})
        mt5_ticket = str(mt5_data.get("ticket", ""))

        order.status = "FILLED"
        order.mt5_ticket = mt5_ticket
        order.price = Decimal(str(mt5_data.get("price", 0)))
        order.save()

        trade = Trade.objects.create(
            user=user,
            symbol=sym,
            position_type=position_type,
            volume=volume,
            open_price=Decimal(str(mt5_data.get("price", 0))),
            stop_loss=stop_loss,
            take_profit=take_profit,
            status="OPEN",
            mt5_ticket=mt5_ticket,
            signal=signal,
            expert_advisor=expert_advisor,
        )

        position = Position.objects.create(
            user=user,
            symbol=sym,
            trade=trade,
            position_type=position_type,
            volume=volume,
            open_price=Decimal(str(mt5_data.get("price", 0))),
            current_price=Decimal(str(mt5_data.get("price", 0))),
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        self._update_daily_monitor(user, Decimal("0"))

        logger.info(
            "Order executed: %s %s %s @ %s, ticket=%s",
            position_type, volume, sym.name, trade.open_price, mt5_ticket,
        )

        return {
            "success": True,
            "trade_id": str(trade.id),
            "order_id": str(order.id),
            "position_id": str(position.id),
            "mt5_ticket": mt5_ticket,
            "open_price": str(trade.open_price),
            "volume": str(volume),
            "symbol": sym.name,
            "type": position_type,
        }

    @transaction.atomic
    def close_trade(
        self, trade_id: str, user, partial_volume: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        from trading.models import Position, Trade

        try:
            trade = Trade.objects.get(id=trade_id, user=user, status="OPEN")
        except Trade.DoesNotExist:
            raise OrderExecutionError("Trade not found or already closed")

        close_volume = partial_volume if partial_volume else trade.volume

        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                self.mt5.close_position(int(trade.mt5_ticket))
            )
        finally:
            loop.close()

        if not result.get("success"):
            raise OrderExecutionError(
                f"MT5 close failed: {result.get('error', 'Unknown error')}"
            )

        mt5_data = result.get("data", {})
        close_price = Decimal(str(mt5_data.get("price", 0)))

        if trade.position_type == "BUY":
            pnl = (close_price - trade.open_price) * trade.volume * Decimal(str(float(trade.symbol.contract_size)))
        else:
            pnl = (trade.open_price - close_price) * trade.volume * Decimal(str(float(trade.symbol.contract_size)))

        trade.close_price = close_price
        trade.profit_loss = pnl
        trade.status = "CLOSED"
        trade.closed_at = timezone.now()
        trade.save()

        try:
            position = Position.objects.get(trade=trade)
            position.delete()
        except Position.DoesNotExist:
            pass

        self._update_daily_monitor(user, pnl)

        logger.info(
            "Trade closed: %s %s @ %s, P&L=%s",
            trade.position_type, trade.symbol.name, close_price, pnl,
        )

        return {
            "success": True,
            "trade_id": str(trade.id),
            "close_price": str(close_price),
            "profit_loss": str(pnl),
            "volume_closed": str(close_volume),
        }

    @transaction.atomic
    def modify_trade(
        self,
        trade_id: str,
        user,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        from trading.models import Trade

        try:
            trade = Trade.objects.get(id=trade_id, user=user, status="OPEN")
        except Trade.DoesNotExist:
            raise OrderExecutionError("Trade not found or not open")

        import asyncio

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                self.mt5.modify_position(
                    int(trade.mt5_ticket),
                    float(stop_loss) if stop_loss else 0.0,
                    float(take_profit) if take_profit else 0.0,
                )
            )
        finally:
            loop.close()

        if not result.get("success"):
            raise OrderExecutionError(
                f"MT5 modify failed: {result.get('error', 'Unknown error')}"
            )

        if stop_loss is not None:
            trade.stop_loss = stop_loss
        if take_profit is not None:
            trade.take_profit = take_profit
        trade.save()

        return {
            "success": True,
            "trade_id": str(trade.id),
            "stop_loss": str(trade.stop_loss),
            "take_profit": str(trade.take_profit),
        }

    def _update_daily_monitor(self, user, pnl: Decimal):
        from risk_management.models import DrawdownMonitor, RiskParameter

        monitor, created = DrawdownMonitor.objects.get_or_create(
            user=user,
            defaults={
                "peak_equity": user.equity,
                "current_equity": user.equity,
                "drawdown_percent": Decimal("0"),
            },
        )

        today = timezone.now().date()
        if monitor.daily_reset_at and monitor.daily_reset_at.date() < today:
            monitor.reset_daily()

        monitor.update_daily_pnl(float(pnl))

        risk_params = RiskParameter.objects.filter(is_active=True).first()
        if risk_params:
            alerts = monitor.check_circuit_breaker(risk_params)
            if alerts:
                from risk_management.models import RiskAlert
                for alert_type, severity, message in alerts:
                    RiskAlert.objects.create(
                        user=user,
                        alert_type=alert_type,
                        severity=severity,
                        message=message,
                    )


order_service = OrderExecutionService()
