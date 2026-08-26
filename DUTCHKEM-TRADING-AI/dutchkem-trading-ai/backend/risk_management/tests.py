# Dutchkem Trading AI — Risk Management Tests

from decimal import Decimal

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestRiskParameterModel:
    def test_create_risk_parameter(self):
        from risk_management.models import RiskParameter

        params = RiskParameter.objects.create(
            name="Default Risk Parameters",
            max_daily_loss=Decimal("2.0"),
            daily_growth_target=Decimal("0.14"),
            daily_target_lock=Decimal("0.4"),
            max_daily_trades=10,
            max_position_size=Decimal("1.0"),
            max_drawdown=Decimal("15.0"),
            min_risk_reward_ratio=Decimal("2.0"),
            target_annual_growth=Decimal("50.0"),
        )
        assert params.max_daily_loss == Decimal("2.0")
        assert params.max_daily_trades == 10


@pytest.mark.django_db
class TestDrawdownMonitor:
    def test_create_drawdown_monitor(self, user):
        from risk_management.models import DrawdownMonitor

        monitor = DrawdownMonitor.objects.create(
            user=user,
            peak_equity=Decimal("10000"),
            current_equity=Decimal("9900"),
            starting_equity_today=Decimal("10000"),
            drawdown_percent=Decimal("1.0"),
            daily_pnl=Decimal("-100"),
            daily_pnl_percent=Decimal("-1.0"),
            daily_trades_count=3,
        )
        assert monitor.drawdown_percent == Decimal("1.0")
        assert monitor.daily_trades_count == 3

    def test_reset_daily(self, user):
        from risk_management.models import DrawdownMonitor

        monitor = DrawdownMonitor.objects.create(
            user=user,
            peak_equity=Decimal("10000"),
            current_equity=Decimal("9900"),
            starting_equity_today=Decimal("10000"),
            drawdown_percent=Decimal("1.0"),
            daily_pnl=Decimal("-100"),
            daily_trades_count=5,
        )
        monitor.reset_daily()
        assert monitor.daily_pnl == 0
        assert monitor.daily_trades_count == 0


@pytest.mark.django_db
class TestRiskEndpoints:
    def test_get_risk_parameters(self, authenticated_client):
        response = authenticated_client.get("/api/v1/risk/parameters/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_drawdown_status(self, authenticated_client):
        response = authenticated_client.get("/api/v1/risk/drawdown/status/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)

    def test_get_risk_dashboard(self, authenticated_client):
        response = authenticated_client.get("/api/v1/risk/dashboard/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)
