# Dutchkem Trading AI — Indicators Tests

from decimal import Decimal

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestTimeframeModel:
    def test_create_timeframe(self):
        from indicators.models import Timeframe

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
        assert tf.code == "M5"
        assert tf.minutes == 5
        assert tf.is_active is True

    def test_timeframe_str(self):
        from indicators.models import Timeframe

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
        assert "M5" in str(tf)


@pytest.mark.django_db
class TestIndicatorModel:
    def test_create_indicator(self):
        from indicators.models import Indicator, IndicatorCategory

        category = IndicatorCategory.objects.create(name="Trend")
        indicator = Indicator.objects.create(
            name="EMA",
            display_name="Exponential Moving Average",
            category=category,
            indicator_type="TREND",
            description="Exponential Moving Average indicator",
            default_parameters={"period": 20},
        )
        assert indicator.name == "EMA"
        assert indicator.indicator_type == "TREND"


@pytest.mark.django_db
class TestIndicatorEndpoints:
    def test_get_timeframes(self, authenticated_client):
        response = authenticated_client.get("/api/v1/indicators/timeframes/")
        assert response.status_code == status.HTTP_200_OK

    def test_get_indicators(self, authenticated_client):
        response = authenticated_client.get("/api/v1/indicators/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)

    def test_get_indicator_categories(self, authenticated_client):
        response = authenticated_client.get("/api/v1/indicators/categories/")
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)
