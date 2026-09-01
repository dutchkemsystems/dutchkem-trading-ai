import uuid

from django.db import models


class MarketData(models.Model):
    """Real-time and historical market data"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.ForeignKey("trading.Symbol", on_delete=models.CASCADE, related_name="market_data")
    timeframe = models.ForeignKey("indicators.Timeframe", on_delete=models.CASCADE, related_name="market_data")
    timestamp = models.DateTimeField(db_index=True)
    open = models.DecimalField(max_digits=20, decimal_places=6)
    high = models.DecimalField(max_digits=20, decimal_places=6)
    low = models.DecimalField(max_digits=20, decimal_places=6)
    close = models.DecimalField(max_digits=20, decimal_places=6)
    volume = models.BigIntegerField(default=0)
    tick_volume = models.BigIntegerField(default=0)
    spread = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["symbol", "timeframe", "-timestamp"]),
        ]
        # This will be converted to TimescaleDB hypertable

    def __str__(self):
        return f"{self.symbol.name} {self.timeframe.code} - {self.timestamp}"


class LivePrice(models.Model):
    """Current live prices for all symbols"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.OneToOneField("trading.Symbol", on_delete=models.CASCADE, related_name="live_price")
    bid = models.DecimalField(max_digits=20, decimal_places=6)
    ask = models.DecimalField(max_digits=20, decimal_places=6)
    spread = models.DecimalField(max_digits=5, decimal_places=2)
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "live prices"

    def __str__(self):
        return f"{self.symbol.name}: {self.bid}/{self.ask}"


class EconomicCalendar(models.Model):
    """Economic events that impact trading"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    currency = models.CharField(max_length=3)
    impact_level = models.CharField(
        max_length=20,
        choices=[
            ("LOW", "Low"),
            ("MEDIUM", "Medium"),
            ("HIGH", "High"),
            ("VERY_HIGH", "Very High"),
        ],
    )
    scheduled_time = models.DateTimeField()
    actual_value = models.CharField(max_length=50, blank=True)
    forecast_value = models.CharField(max_length=50, blank=True)
    previous_value = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["scheduled_time"]

    def __str__(self):
        return f"{self.event_name} - {self.currency} - {self.scheduled_time}"


class MarketSentiment(models.Model):
    """Market sentiment analysis"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.ForeignKey("trading.Symbol", on_delete=models.CASCADE, related_name="sentiments")
    timestamp = models.DateTimeField(auto_now_add=True)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=2)  # -100 to 100
    fear_greed_index = models.DecimalField(max_digits=5, decimal_places=2)  # 0-100
    news_sentiment = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    social_sentiment = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    institutional_flow = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    data_sources = models.JSONField(default=list)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.symbol.name} Sentiment: {self.sentiment_score}"
