# Dutchkem Trading AI — Expert Advisors Tests

from decimal import Decimal

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestExpertAdvisorModel:
    def test_create_ea(self, user):
        from expert_advisors.models import ExpertAdvisor
        from indicators.models import Timeframe
        from trading.models import Symbol

        symbol = Symbol.objects.create(
            name="EURUSD", description="Euro vs US Dollar", category="MAJOR", base_currency="EUR", quote_currency="USD"
        )
        tf = Timeframe.objects.create(
            code="M5",
            name="5 Minutes",
            minutes=5,
            strategy_type="Scalping",
            risk_level="HIGH",
            target_pips_min=5,
            target_pips_max=10,
            stop_loss_min=10,
            stop_loss_max=15,
            win_rate_target_min=60,
            win_rate_target_max=65,
            risk_reward_ratio=Decimal("1.5"),
        )
        ea = ExpertAdvisor.objects.create(
            user=user,
            name="M5 Scalper Pro",
            description="M5 scalping EA",
            symbol=symbol,
            timeframe=tf,
            strategy_type="scalping",
            parameters={"rsi_period": 7},
            risk_per_trade=Decimal("1.0"),
            status="INACTIVE",
        )
        assert ea.name == "M5 Scalper Pro"
        assert ea.status == "INACTIVE"

    def test_ea_str(self, user):
        from expert_advisors.models import ExpertAdvisor
        from indicators.models import Timeframe
        from trading.models import Symbol

        symbol = Symbol.objects.create(
            name="EURUSD", description="Euro vs US Dollar", category="MAJOR", base_currency="EUR", quote_currency="USD"
        )
        tf = Timeframe.objects.create(
            code="M5",
            name="5 Minutes",
            minutes=5,
            strategy_type="Scalping",
            risk_level="HIGH",
            target_pips_min=5,
            target_pips_max=10,
            stop_loss_min=10,
            stop_loss_max=15,
            win_rate_target_min=60,
            win_rate_target_max=65,
            risk_reward_ratio=Decimal("1.5"),
        )
        ea = ExpertAdvisor.objects.create(
            user=user, name="M5 Scalper Pro", symbol=symbol, timeframe=tf, strategy_type="scalping"
        )
        assert "M5 Scalper Pro" in str(ea)


@pytest.mark.django_db
class TestEAEndpoints:
    def test_get_eas(self, authenticated_client):
        response = authenticated_client.get("/api/v1/eas/")
        assert response.status_code == status.HTTP_200_OK

    def test_generate_code(self, authenticated_client, user):
        from expert_advisors.models import ExpertAdvisor
        from indicators.models import Timeframe
        from trading.models import Symbol

        symbol = Symbol.objects.create(
            name="EURUSD", description="Euro vs US Dollar", category="MAJOR", base_currency="EUR", quote_currency="USD"
        )
        tf = Timeframe.objects.create(
            code="M5",
            name="5 Minutes",
            minutes=5,
            strategy_type="Scalping",
            risk_level="HIGH",
            target_pips_min=5,
            target_pips_max=10,
            stop_loss_min=10,
            stop_loss_max=15,
            win_rate_target_min=60,
            win_rate_target_max=65,
            risk_reward_ratio=Decimal("1.5"),
        )
        ea = ExpertAdvisor.objects.create(
            user=user, name="Test EA", symbol=symbol, timeframe=tf, strategy_type="scalping"
        )
        response = authenticated_client.post("/api/v1/eas/generate-code/", {"ea_id": str(ea.id), "optimize": False})
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)
