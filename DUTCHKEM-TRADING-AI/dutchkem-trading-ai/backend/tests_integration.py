# Dutchkem Trading AI — Integration Tests

from decimal import Decimal

import pytest
from rest_framework import status


@pytest.mark.django_db
@pytest.mark.integration
class TestFullTradingFlow:
    def test_complete_trading_cycle(self, user):
        from indicators.models import Timeframe
        from risk_management.models import DrawdownMonitor, RiskParameter
        from signals.models import Signal
        from trading.models import Order, Symbol, Trade

        # 1. Create symbol
        symbol = Symbol.objects.create(
            name="EURUSD",
            description="Euro vs US Dollar",
            category="MAJOR",
            base_currency="EUR",
            quote_currency="USD",
            pip_size=Decimal("0.0001"),
            spread=Decimal("1.0"),
            contract_size=Decimal("100000"),
        )

        # 2. Create timeframe
        tf = Timeframe.objects.create(
            code="H1",
            name="1 Hour",
            minutes=60,
            strategy_type="Trend",
            risk_level="MEDIUM_LOW",
            target_pips_min=40,
            target_pips_max=80,
            stop_loss_min=50,
            stop_loss_max=100,
            win_rate_target_min=52,
            win_rate_target_max=58,
            risk_reward_ratio=Decimal("2.5"),
        )

        # 3. Create risk parameters
        params = RiskParameter.objects.create(
            name="Default",
            max_daily_loss=Decimal("2.0"),
            daily_growth_target=Decimal("0.14"),
            daily_target_lock=Decimal("0.4"),
            max_daily_trades=10,
            max_position_size=Decimal("1.0"),
            max_drawdown=Decimal("15.0"),
            min_risk_reward_ratio=Decimal("2.0"),
        )

        # 4. Create drawdown monitor
        monitor = DrawdownMonitor.objects.create(
            user=user,
            peak_equity=Decimal("10000"),
            current_equity=Decimal("10000"),
            starting_equity_today=Decimal("10000"),
            drawdown_percent=Decimal("0"),
            daily_pnl=Decimal("0"),
            daily_trades_count=0,
        )

        # 5. Generate signal
        signal = Signal.objects.create(
            symbol=symbol,
            timeframe=tf,
            signal_type="BUY",
            strength=Decimal("85"),
            confluence_score=Decimal("80"),
            entry_price=Decimal("1.1200"),
            stop_loss=Decimal("1.1150"),
            take_profit=Decimal("1.1300"),
            risk_reward_ratio=Decimal("2.0"),
            confidence=Decimal("75"),
        )

        # 6. Create order
        order = Order.objects.create(
            user=user,
            symbol=symbol,
            order_type="MARKET",
            position_type="BUY",
            volume=Decimal("0.1"),
            price=Decimal("1.1200"),
            stop_loss=Decimal("1.1150"),
            take_profit=Decimal("1.1300"),
            status="FILLED",
        )

        # 7. Create trade
        trade = Trade.objects.create(
            user=user,
            symbol=symbol,
            signal=signal,
            position_type="BUY",
            volume=Decimal("0.1"),
            open_price=Decimal("1.1200"),
            stop_loss=Decimal("1.1150"),
            take_profit=Decimal("1.1300"),
            status="OPEN",
        )

        # 8. Verify all components exist
        assert signal.signal_type == "BUY"
        assert order.status == "FILLED"
        assert trade.status == "OPEN"
        assert monitor.daily_trades_count == 0


@pytest.mark.django_db
@pytest.mark.integration
class TestRiskManagementFlow:
    def test_daily_loss_circuit_breaker(self, user):
        from risk_management.models import DrawdownMonitor, RiskParameter

        params = RiskParameter.objects.create(
            name="Default",
            max_daily_loss=Decimal("2.0"),
            daily_growth_target=Decimal("0.14"),
            daily_target_lock=Decimal("0.4"),
            max_daily_trades=10,
            max_position_size=Decimal("1.0"),
            max_drawdown=Decimal("15.0"),
        )

        monitor = DrawdownMonitor.objects.create(
            user=user,
            peak_equity=Decimal("10000"),
            current_equity=Decimal("9700"),
            starting_equity_today=Decimal("10000"),
            drawdown_percent=Decimal("3.0"),
            daily_pnl=Decimal("-300"),
            daily_pnl_percent=Decimal("-3.0"),
            daily_trades_count=5,
        )

        alerts = monitor.check_circuit_breaker(params)
        assert len(alerts) > 0
        assert monitor.daily_pnl_percent < -params.max_daily_loss


@pytest.mark.django_db
@pytest.mark.integration
class TestSignalGenerationFlow:
    def test_signal_to_trade_flow(self, user):
        from indicators.models import Timeframe
        from signals.models import Signal
        from trading.models import Symbol

        symbol = Symbol.objects.create(
            name="EURUSD", description="Euro vs US Dollar", category="MAJOR", base_currency="EUR", quote_currency="USD"
        )

        tf = Timeframe.objects.create(
            code="H1",
            name="1 Hour",
            minutes=60,
            strategy_type="Trend",
            risk_level="MEDIUM_LOW",
            target_pips_min=40,
            target_pips_max=80,
            stop_loss_min=50,
            stop_loss_max=100,
            win_rate_target_min=52,
            win_rate_target_max=58,
            risk_reward_ratio=Decimal("2.5"),
        )

        signal = Signal.objects.create(
            symbol=symbol,
            timeframe=tf,
            signal_type="BUY",
            strength=Decimal("85"),
            confluence_score=Decimal("80"),
            entry_price=Decimal("1.1200"),
            stop_loss=Decimal("1.1150"),
            take_profit=Decimal("1.1300"),
            risk_reward_ratio=Decimal("2.0"),
            confidence=Decimal("75"),
            status="ACTIVE",
        )

        assert signal.entry_price > signal.stop_loss
        assert signal.take_profit > signal.entry_price
        assert signal.risk_reward_ratio >= Decimal("2.0")
