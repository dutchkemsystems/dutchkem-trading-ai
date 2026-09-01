from django.test import TestCase
from indicators.models import Timeframe, Indicator, IndicatorCategory, IndicatorValue
from decimal import Decimal


class TimeframeModelTest(TestCase):
    def test_create_timeframe(self):
        tf = Timeframe.objects.create(
            code="M5", name="5 Minute", minutes=5,
            strategy_type="Scalping", risk_level="HIGH",
            target_pips_min=5, target_pips_max=10,
            stop_loss_min=10, stop_loss_max=15,
            win_rate_target_min=Decimal("55.00"),
            win_rate_target_max=Decimal("65.00"),
            risk_reward_ratio=Decimal("1.50"),
        )
        self.assertEqual(tf.code, "M5")
        self.assertEqual(tf.minutes, 5)

    def test_timeframe_str(self):
        tf = Timeframe.objects.create(
            code="H1", name="1 Hour", minutes=60,
            strategy_type="Trend", risk_level="MEDIUM",
            target_pips_min=40, target_pips_max=80,
            stop_loss_min=50, stop_loss_max=100,
            win_rate_target_min=Decimal("45.00"),
            win_rate_target_max=Decimal("55.00"),
            risk_reward_ratio=Decimal("2.00"),
        )
        self.assertEqual(str(tf), "H1 - 1 Hour")


class IndicatorCategoryTest(TestCase):
    def test_create_category(self):
        cat = IndicatorCategory.objects.create(
            name="Trend", description="Trend indicators", icon="trending-up"
        )
        self.assertEqual(cat.name, "Trend")


class IndicatorModelTest(TestCase):
    def setUp(self):
        self.category = IndicatorCategory.objects.create(
            name="Momentum", description="Momentum indicators", icon="speed"
        )

    def test_create_indicator(self):
        indicator = Indicator.objects.create(
            name="RSI", display_name="Relative Strength Index",
            category=self.category, indicator_type="MOMENTUM",
            description="Measures speed of price changes",
            default_parameters={"period": 14},
        )
        self.assertEqual(indicator.name, "RSI")
