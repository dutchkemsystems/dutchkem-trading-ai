import uuid

from django.conf import settings
from django.db import models


class CachedTradeSummary(models.Model):
    """Cache expensive trade summary queries"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cached_trade_summaries")
    period = models.CharField(
        max_length=20,
        choices=[
            ("TODAY", "Today"),
            ("WEEK", "This Week"),
            ("MONTH", "This Month"),
            ("ALL_TIME", "All Time"),
        ],
    )
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    average_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    best_trade = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    worst_trade = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    profit_factor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cached_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-cached_at"]
        unique_together = ["user", "period"]

    def __str__(self):
        return f"{self.user.username} - {self.period} - {self.cached_at}"


class CachedDailyPerformance(models.Model):
    """Cache daily performance metrics"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cached_daily_performances")
    date = models.DateField()
    daily_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    daily_pnl_percent = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        unique_together = ["user", "date"]

    def __str__(self):
        return f"{self.user.username} - {self.date} - P&L: {self.daily_pnl}"


class CachedSymbolBreakdown(models.Model):
    """Cache P&L breakdown by symbol"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cached_symbol_breakdowns")
    symbol_name = models.CharField(max_length=20)
    total_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    period = models.CharField(max_length=20, default="ALL_TIME")
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-total_pnl"]
        unique_together = ["user", "symbol_name", "period"]

    def __str__(self):
        return f"{self.user.username} - {self.symbol_name} - {self.total_pnl}"
