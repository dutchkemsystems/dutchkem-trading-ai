import uuid

from django.conf import settings
from django.db import models


class RiskParameter(models.Model):
    """
    Global risk parameters for the trading system

    Daily Focused Targets:
    - Daily Growth: 0.14% per day (40% annualized / 365)
    - Monthly Growth: ~4.2% per month
    - Annual Growth: ~50%+ per year (compounded daily)
    - Daily Loss Limit: 2% max daily loss
    - Daily Target Lock: Trading stops at 0.4% daily gain
    - Max Drawdown: 15%
    - Position Size: 1% per trade
    - Max Daily Trades: 10
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    # Daily risk limits
    max_daily_loss = models.DecimalField(
        max_digits=5, decimal_places=2, default=2.0, help_text="Maximum daily loss as percentage (default: 2%)"
    )
    daily_growth_target = models.DecimalField(
        max_digits=5, decimal_places=4, default=0.14, help_text="Daily growth target as percentage (default: 0.14%)"
    )
    daily_target_lock = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.4,
        help_text="Daily target lock - trading stops after this gain (default: 0.4%)",
    )
    max_daily_trades = models.IntegerField(default=10, help_text="Maximum number of trades per day (default: 10)")

    # Position sizing
    max_position_size = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        help_text="Maximum position size as percentage per trade (default: 1%)",
    )
    max_open_positions = models.IntegerField(default=5, help_text="Maximum open positions per instrument (default: 5)")

    # Drawdown limits
    max_drawdown = models.DecimalField(
        max_digits=5, decimal_places=2, default=15.0, help_text="Maximum drawdown as percentage (default: 15%)"
    )

    # Correlation and risk-reward
    max_correlation = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.70, help_text="Maximum correlation between positions (default: 0.70)"
    )
    min_risk_reward_ratio = models.DecimalField(
        max_digits=5, decimal_places=2, default=2.0, help_text="Minimum risk-reward ratio (default: 1:2)"
    )

    # Performance targets
    target_daily_growth = models.DecimalField(
        max_digits=5, decimal_places=4, default=0.14, help_text="Target daily growth percentage (default: 0.14%)"
    )
    target_monthly_growth = models.DecimalField(
        max_digits=5, decimal_places=2, default=4.2, help_text="Target monthly growth percentage (default: 4.2%)"
    )
    target_annual_growth = models.DecimalField(
        max_digits=5, decimal_places=2, default=50.0, help_text="Target annual growth percentage (default: 50%+)"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "risk parameters"

    def __str__(self):
        return self.name

    @property
    def daily_loss_limit_amount(self):
        """Calculate daily loss limit amount based on equity"""
        return lambda equity: equity * (self.max_daily_loss / 100)

    @property
    def daily_target_amount(self):
        """Calculate daily target amount based on equity"""
        return lambda equity: equity * (self.daily_growth_target / 100)


class PositionSizing(models.Model):
    """
    Position sizing calculations

    Daily Risk Budget:
    - Risk per trade: 1% of equity
    - Daily loss limit: 2% of equity
    - Max daily trades: 10
    - Adjusts based on remaining daily budget
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="position_sizings")
    symbol = models.ForeignKey("trading.Symbol", on_delete=models.CASCADE)
    timeframe = models.ForeignKey(
        "indicators.Timeframe", on_delete=models.SET_NULL, null=True, related_name="position_sizings"
    )

    # Risk parameters
    risk_per_trade = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.0, help_text="Risk per trade as percentage (default: 1%)"
    )
    account_equity = models.DecimalField(max_digits=20, decimal_places=2)
    risk_amount = models.DecimalField(max_digits=20, decimal_places=2)
    stop_loss_pips = models.IntegerField()
    position_size = models.DecimalField(max_digits=10, decimal_places=2)

    # Daily tracking
    daily_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    daily_trades_count = models.IntegerField(default=0)
    remaining_daily_budget = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-calculated_at"]

    def __str__(self):
        return f"{self.user.username} - {self.symbol.name} - Size: {self.position_size}"


class DrawdownMonitor(models.Model):
    """
    Track drawdown and trigger circuit breakers

    Circuit Breakers:
    - Daily loss limit: 2% of equity
    - Max drawdown: 15% of equity
    - Daily target lock: Trading stops at 0.4% daily gain
    - Max daily trades: 10
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="drawdown_monitors")

    # Equity tracking
    peak_equity = models.DecimalField(max_digits=20, decimal_places=2)
    current_equity = models.DecimalField(max_digits=20, decimal_places=2)
    starting_equity_today = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # Drawdown tracking
    drawdown_percent = models.DecimalField(max_digits=5, decimal_places=2)

    # Daily tracking
    daily_pnl = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    daily_pnl_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    daily_loss_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    daily_trades_count = models.IntegerField(default=0)

    # Circuit breaker status
    is_daily_loss_triggered = models.BooleanField(default=False)
    is_drawdown_triggered = models.BooleanField(default=False)
    is_daily_target_triggered = models.BooleanField(default=False)
    is_max_trades_triggered = models.BooleanField(default=False)
    is_circuit_breaker_triggered = models.BooleanField(default=False)

    # Trigger timestamps
    triggered_at = models.DateTimeField(blank=True, null=True)
    daily_reset_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - DD: {self.drawdown_percent}% - Daily P&L: {self.daily_pnl_percent}%"

    def check_circuit_breaker(self, risk_params):
        """Check all circuit breakers and return status"""
        alerts = []

        # Check daily loss limit (2%)
        if self.daily_loss_percent >= risk_params.max_daily_loss:
            self.is_daily_loss_triggered = True
            self.is_circuit_breaker_triggered = True
            alerts.append(("DAILY_LOSS", "CRITICAL", f"Daily loss limit reached: {self.daily_loss_percent}%"))

        # Check max drawdown (15%)
        if self.drawdown_percent >= risk_params.max_drawdown:
            self.is_drawdown_triggered = True
            self.is_circuit_breaker_triggered = True
            alerts.append(("DRAWDOWN", "CRITICAL", f"Max drawdown reached: {self.drawdown_percent}%"))

        # Check daily target lock (0.4%)
        if self.daily_pnl_percent >= risk_params.daily_target_lock:
            self.is_daily_target_triggered = True
            self.is_circuit_breaker_triggered = True
            alerts.append(("DAILY_TARGET", "INFO", f"Daily target reached: {self.daily_pnl_percent}%"))

        # Check max daily trades (10)
        if self.daily_trades_count >= risk_params.max_daily_trades:
            self.is_max_trades_triggered = True
            self.is_circuit_breaker_triggered = True
            alerts.append(("MAX_TRADES", "HIGH", f"Max daily trades reached: {self.daily_trades_count}"))

        if alerts:
            self.triggered_at = self.updated_at
            self.save()

        return alerts

    def update_daily_pnl(self, trade_pnl):
        """Update daily P&L after a trade"""
        self.daily_pnl += trade_pnl
        self.daily_trades_count += 1

        if self.starting_equity_today > 0:
            self.daily_pnl_percent = (self.daily_pnl / self.starting_equity_today) * 100
            if self.daily_pnl < 0:
                self.daily_loss_percent = abs(self.daily_pnl_percent)

        self.save()

    def reset_daily(self):
        """Reset daily counters"""
        self.starting_equity_today = self.current_equity
        self.daily_pnl = 0
        self.daily_pnl_percent = 0
        self.daily_loss_percent = 0
        self.daily_trades_count = 0
        self.is_daily_loss_triggered = False
        self.is_daily_target_triggered = False
        self.is_max_trades_triggered = False
        self.is_circuit_breaker_triggered = False
        self.daily_reset_at = self.updated_at
        self.save()

    def get_status(self):
        """Get current risk status"""
        return {
            "equity": str(self.current_equity),
            "peak_equity": str(self.peak_equity),
            "drawdown_percent": str(self.drawdown_percent),
            "daily_pnl": str(self.daily_pnl),
            "daily_pnl_percent": str(self.daily_pnl_percent),
            "daily_trades_count": self.daily_trades_count,
            "is_circuit_breaker_triggered": self.is_circuit_breaker_triggered,
            "alerts": {
                "daily_loss": self.is_daily_loss_triggered,
                "drawdown": self.is_drawdown_triggered,
                "daily_target": self.is_daily_target_triggered,
                "max_trades": self.is_max_trades_triggered,
            },
        }


class CorrelationMatrix(models.Model):
    """Track correlation between positions"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol_pair = models.CharField(max_length=20)  # e.g., "EURUSD-GBPUSD"
    correlation = models.DecimalField(max_digits=5, decimal_places=4)
    timeframe = models.ForeignKey("indicators.Timeframe", on_delete=models.CASCADE)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-calculated_at"]
        unique_together = ["symbol_pair", "timeframe"]

    def __str__(self):
        return f"{self.symbol_pair}: {self.correlation}"


class RiskAlert(models.Model):
    """Risk alerts and notifications for daily risk management"""

    ALERT_TYPES = [
        ("DRAWDOWN", "Drawdown Alert"),
        ("DAILY_LOSS", "Daily Loss Alert"),
        ("DAILY_TARGET", "Daily Target Alert"),
        ("POSITION_SIZE", "Position Size Alert"),
        ("CORRELATION", "Correlation Alert"),
        ("CIRCUIT_BREAKER", "Circuit Breaker Triggered"),
        ("MAX_DAILY_TRADES", "Max Daily Trades Reached"),
        ("DAILY_TARGET_LOCK", "Daily Target Lock Triggered"),
        ("MARGIN_CALL", "Margin Call"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="risk_alerts")
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(
        max_length=10,
        choices=[
            ("LOW", "Low"),
            ("MEDIUM", "Medium"),
            ("HIGH", "High"),
            ("CRITICAL", "Critical"),
        ],
    )
    message = models.TextField()
    data = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.alert_type} - {self.severity} - {self.user.username}"


class DailyPerformance(models.Model):
    """Track daily trading performance"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_performances")
    date = models.DateField()

    # Daily metrics
    starting_equity = models.DecimalField(max_digits=20, decimal_places=2)
    ending_equity = models.DecimalField(max_digits=20, decimal_places=2)
    daily_pnl = models.DecimalField(max_digits=20, decimal_places=2)
    daily_pnl_percent = models.DecimalField(max_digits=5, decimal_places=4)

    # Trade metrics
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # P&L metrics
    total_profit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_loss = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    avg_win = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    avg_loss = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # Risk metrics
    max_drawdown = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    risk_reward_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Timeframe breakdown
    timeframe_performance = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        unique_together = ["user", "date"]

    def __str__(self):
        return f"{self.user.username} - {self.date} - P&L: {self.daily_pnl_percent}%"

    def calculate_metrics(self):
        """Calculate daily metrics from trades"""
        from trading.models import Trade

        trades = Trade.objects.filter(user=self.user, closed_at__date=self.date, status="CLOSED")

        self.total_trades = trades.count()
        self.winning_trades = trades.filter(profit_loss__gt=0).count()
        self.losing_trades = trades.filter(profit_loss__lt=0).count()

        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100

        self.total_profit = sum(t.profit_loss for t in trades if t.profit_loss > 0)
        self.total_loss = sum(abs(t.profit_loss) for t in trades if t.profit_loss < 0)

        if self.winning_trades > 0:
            self.avg_win = self.total_profit / self.winning_trades
        if self.losing_trades > 0:
            self.avg_loss = self.total_loss / self.losing_trades

        if self.avg_loss > 0:
            self.risk_reward_ratio = self.avg_win / self.avg_loss

        self.daily_pnl = self.total_profit - self.total_loss
        if self.starting_equity > 0:
            self.daily_pnl_percent = (self.daily_pnl / self.starting_equity) * 100

        self.save()
