import uuid

from django.conf import settings
from django.db import models


class Signal(models.Model):
    SIGNAL_STRENGTHS = [
        ("STRONG_BUY", "Strong Buy"),
        ("BUY", "Buy"),
        ("NEUTRAL", "Neutral"),
        ("SELL", "Sell"),
        ("STRONG_SELL", "Strong Sell"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.ForeignKey("trading.Symbol", on_delete=models.CASCADE, related_name="signals")
    timeframe = models.ForeignKey("indicators.Timeframe", on_delete=models.CASCADE, related_name="signals")
    signal_type = models.CharField(max_length=20, choices=SIGNAL_STRENGTHS)
    strength = models.DecimalField(max_digits=5, decimal_places=2)  # 0-100

    # Confluence scoring
    confluence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    indicator_agreement = models.JSONField(default=dict)  # Which indicators agree
    pattern_detected = models.CharField(max_length=100, blank=True)

    # Price levels
    entry_price = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)
    risk_reward_ratio = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    # Multi-timeframe confluence
    h4_trend = models.CharField(max_length=10, blank=True)  # UP, DOWN, SIDEWAYS
    h1_trend = models.CharField(max_length=10, blank=True)
    m15_trend = models.CharField(max_length=10, blank=True)
    mtf_confluence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Metadata
    generated_by = models.CharField(max_length=50, default="system")  # system, agent, ea
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["symbol", "timeframe", "-created_at"]),
            models.Index(fields=["signal_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.signal_type} {self.symbol.name} ({self.timeframe.code}) - {self.strength}%"


class SignalHistory(models.Model):
    """Track signal performance for backtesting and accuracy measurement"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signal = models.ForeignKey(Signal, on_delete=models.CASCADE, related_name="history")
    outcome = models.CharField(
        max_length=20,
        choices=[
            ("WIN", "Win"),
            ("LOSS", "Loss"),
            ("BREAKEVEN", "Breakeven"),
            ("PENDING", "Pending"),
        ],
        default="PENDING",
    )
    actual_pips = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_favorable = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_adverse = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    closed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-closed_at"]

    def __str__(self):
        return f"{self.signal} - {self.outcome}"


class ConfluenceScore(models.Model):
    """Multi-timeframe confluence scoring"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.ForeignKey("trading.Symbol", on_delete=models.CASCADE, related_name="confluence_scores")
    timestamp = models.DateTimeField(auto_now_add=True)

    # Individual timeframe scores
    m5_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    m15_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    m30_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    h1_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    h2_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    h4_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Overall confluence
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    direction = models.CharField(
        max_length=10,
        choices=[
            ("LONG", "Long"),
            ("SHORT", "Short"),
            ("NEUTRAL", "Neutral"),
        ],
        default="NEUTRAL",
    )

    # Timeframe agreement
    higher_tf_agreement = models.BooleanField(default=False)
    all_tf_aligned = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.symbol.name} Confluence: {self.total_score}% ({self.direction})"
