import uuid

from django.conf import settings
from django.db import models


class Timeframe(models.Model):
    """Trading timeframes: M5, M15, M30, H1, H2, H4"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=5, unique=True)  # M5, M15, M30, H1, H2, H4
    name = models.CharField(max_length=50)
    minutes = models.IntegerField()  # 5, 15, 30, 60, 120, 240
    strategy_type = models.CharField(max_length=50)
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ("HIGH", "High"),
            ("MEDIUM_HIGH", "Medium-High"),
            ("MEDIUM", "Medium"),
            ("MEDIUM_LOW", "Medium-Low"),
            ("LOW_MEDIUM", "Low-Medium"),
            ("LOW", "Low"),
        ],
    )
    target_pips_min = models.IntegerField()
    target_pips_max = models.IntegerField()
    stop_loss_min = models.IntegerField()
    stop_loss_max = models.IntegerField()
    win_rate_target_min = models.DecimalField(max_digits=5, decimal_places=2)
    win_rate_target_max = models.DecimalField(max_digits=5, decimal_places=2)
    risk_reward_ratio = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["minutes"]
        verbose_name_plural = "timeframes"

    def __str__(self):
        return f"{self.code} - {self.name}"


class IndicatorCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "indicator categories"

    def __str__(self):
        return self.name


class Indicator(models.Model):
    INDICATOR_TYPES = [
        ("TREND", "Trend"),
        ("MOMENTUM", "Momentum"),
        ("VOLATILITY", "Volatility"),
        ("VOLUME", "Volume"),
        ("OSCILLATOR", "Oscillator"),
        ("CUSTOM", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    category = models.ForeignKey(IndicatorCategory, on_delete=models.CASCADE, related_name="indicators")
    indicator_type = models.CharField(max_length=20, choices=INDICATOR_TYPES)
    description = models.TextField()
    formula = models.TextField(blank=True)
    default_parameters = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    # Timeframe suitability
    suitable_timeframes = models.ManyToManyField(Timeframe, related_name="suitable_indicators")

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.display_name


class IndicatorValue(models.Model):
    """Time-series indicator values stored in PostgreSQL (will be TimescaleDB hypertable)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.ForeignKey("trading.Symbol", on_delete=models.CASCADE, related_name="indicator_values")
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name="values")
    timeframe = models.ForeignKey(Timeframe, on_delete=models.CASCADE, related_name="indicator_values")
    timestamp = models.DateTimeField(db_index=True)
    value = models.JSONField()
    signal = models.CharField(
        max_length=20,
        choices=[
            ("STRONG_BUY", "Strong Buy"),
            ("BUY", "Buy"),
            ("NEUTRAL", "Neutral"),
            ("SELL", "Sell"),
            ("STRONG_SELL", "Strong Sell"),
        ],
        default="NEUTRAL",
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["symbol", "indicator", "timeframe", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.symbol.name} - {self.indicator.name} ({self.timeframe.code})"


class TimeframeIndicatorConfig(models.Model):
    """Configuration for which indicators to use per timeframe"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timeframe = models.ForeignKey(Timeframe, on_delete=models.CASCADE, related_name="indicator_configs")
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name="timeframe_configs")
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    parameters = models.JSONField(default=dict)
    priority = models.IntegerField(default=0)

    class Meta:
        unique_together = ["timeframe", "indicator"]
        ordering = ["-priority", "indicator__name"]
