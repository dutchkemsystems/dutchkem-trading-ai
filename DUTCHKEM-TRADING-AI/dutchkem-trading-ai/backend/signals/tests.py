# Dutchkem Trading AI — Signals Tests

from decimal import Decimal

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestSignalModel:
    def test_create_signal(self, user):
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
        )
        assert signal.signal_type == "BUY"
        assert signal.strength == Decimal("85")


@pytest.mark.django_db
class TestSignalEndpoints:
    def test_get_signals(self, authenticated_client):
        response = authenticated_client.get("/api/v1/signals/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_active_signals(self, authenticated_client):
        response = authenticated_client.get("/api/v1/signals/active/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)
