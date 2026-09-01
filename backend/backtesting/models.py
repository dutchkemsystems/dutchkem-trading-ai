import uuid

from django.conf import settings
from django.db import models


class BacktestResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="backtest_results")
    name = models.CharField(max_length=200)
    symbol = models.CharField(max_length=20)
    timeframe = models.CharField(max_length=10)
    strategy = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    initial_balance = models.DecimalField(max_digits=20, decimal_places=2, default=10000)
    final_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_pnl_percent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    profit_factor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_drawdown = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    parameters = models.JSONField(default=dict)
    trades = models.JSONField(default=list)
    equity_curve = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.symbol} {self.timeframe}"
