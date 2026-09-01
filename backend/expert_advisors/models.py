import uuid

from django.conf import settings
from django.db import models


class ExpertAdvisor(models.Model):
    EA_STATUS_CHOICES = [
        ("INACTIVE", "Inactive"),
        ("BACKTESTING", "Backtesting"),
        ("OPTIMIZING", "Optimizing"),
        ("LIVE", "Live"),
        ("PAUSED", "Paused"),
        ("ERROR", "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expert_advisors")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=20, default="1.0.0")
    status = models.CharField(max_length=20, choices=EA_STATUS_CHOICES, default="INACTIVE")

    # EA Configuration
    symbol = models.ForeignKey("trading.Symbol", on_delete=models.CASCADE, related_name="expert_advisors")
    timeframe = models.ForeignKey("indicators.Timeframe", on_delete=models.CASCADE, related_name="expert_advisors")
    strategy_type = models.CharField(max_length=50)
    parameters = models.JSONField(default=dict)

    # Risk Settings
    risk_per_trade = models.DecimalField(max_digits=5, decimal_places=2, default=2.0)
    max_positions = models.IntegerField(default=1)
    use_stop_loss = models.BooleanField(default=True)
    use_take_profit = models.BooleanField(default=True)
    trailing_stop = models.BooleanField(default=False)
    trailing_stop_pips = models.IntegerField(default=0)

    # Performance
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    total_profit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    max_drawdown = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sharpe_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # MQL5 Code
    mql5_code = models.TextField(blank=True)
    compiled = models.BooleanField(default=False)
    mt5_ticket = models.CharField(max_length=50, blank=True)

    # Metadata
    ai_generated = models.BooleanField(default=False)
    backtest_results = models.JSONField(default=dict)
    optimization_history = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deployed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.symbol.name} {self.timeframe.code}) - {self.status}"


class EABacktestResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ea = models.ForeignKey(ExpertAdvisor, on_delete=models.CASCADE, related_name="backtest_results_detail")
    start_date = models.DateField()
    end_date = models.DateField()
    initial_balance = models.DecimalField(max_digits=20, decimal_places=2)
    final_balance = models.DecimalField(max_digits=20, decimal_places=2)
    total_return = models.DecimalField(max_digits=10, decimal_places=2)
    max_drawdown = models.DecimalField(max_digits=5, decimal_places=2)
    sharpe_ratio = models.DecimalField(max_digits=5, decimal_places=2)
    total_trades = models.IntegerField()
    winning_trades = models.IntegerField()
    losing_trades = models.IntegerField()
    profit_factor = models.DecimalField(max_digits=5, decimal_places=2)
    equity_curve = models.JSONField(default=list)
    trade_history = models.JSONField(default=list)
    parameters_used = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ea.name} - {self.start_date} to {self.end_date}"


class EADeployment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ea = models.ForeignKey(ExpertAdvisor, on_delete=models.CASCADE, related_name="deployments")
    mt5_account = models.CharField(max_length=50)
    mt5_server = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=[
            ("DEPLOYING", "Deploying"),
            ("ACTIVE", "Active"),
            ("STOPPED", "Stopped"),
            ("ERROR", "Error"),
        ],
    )
    deployed_at = models.DateTimeField(auto_now_add=True)
    stopped_at = models.DateTimeField(blank=True, null=True)
    logs = models.JSONField(default=list)

    class Meta:
        ordering = ["-deployed_at"]

    def __str__(self):
        return f"{self.ea.name} - {self.mt5_account} - {self.status}"
