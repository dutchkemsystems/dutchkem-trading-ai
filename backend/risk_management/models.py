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
    - Max Drawdown: 15% (standard) / 20-40% (Gold Edge)
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

    # ── Gold Edge specific risk parameters ──────────────────────────
    # Gold Edge allows higher drawdown tolerance (20-40%) due to the
    # nature of gold/XAUUSD swings. Circuit breakers are ATR-adjusted.
    gold_edge_enabled = models.BooleanField(
        default=False,
        help_text="Enable Gold Edge specific risk overrides",
    )
    gold_edge_max_drawdown = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.0,
        help_text="Gold Edge max drawdown tolerance as percentage (default: 30%, range 20-40%)",
    )
    gold_edge_atr_position_sizing = models.BooleanField(
        default=True,
        help_text="Use ATR-based position sizing for Gold Edge trades",
    )
    gold_edge_atr_risk_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.5,
        help_text="ATR-based position size multiplier (default: 1.5x for gold volatility)",
    )
    gold_edge_circuit_breaker_loss = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.0,
        help_text="Gold Edge daily loss circuit breaker (default: 5%, higher than standard 2%)",
    )
    gold_edge_circuit_breaker_consecutive_losses = models.IntegerField(
        default=4,
        help_text="Consecutive losing trades to trigger Gold Edge circuit breaker (default: 4)",
    )
    gold_edge_min_risk_reward = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.5,
        help_text="Gold Edge minimum risk-reward ratio (default: 1.5, lower than standard 2.0)",
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

    def get_max_drawdown(self, strategy: str = "standard") -> float:
        """Return the appropriate max drawdown for the given strategy."""
        if strategy == "gold_edge" and self.gold_edge_enabled:
            return float(self.gold_edge_max_drawdown)
        return float(self.max_drawdown)

    def get_min_risk_reward(self, strategy: str = "standard") -> float:
        """Return the appropriate min risk-reward for the given strategy."""
        if strategy == "gold_edge" and self.gold_edge_enabled:
            return float(self.gold_edge_min_risk_reward)
        return float(self.min_risk_reward_ratio)


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


class GoldEdgeRiskParameter(models.Model):
    """
    Gold Edge specific risk parameters.

    Gold Edge (Dutchkem 2.0) allows higher risk tolerance than the standard
    trading system due to the strategy's focus on high-probability ATR-based entries.

    Key differences from standard RiskParameter:
    - Max drawdown tolerance: 20-40% (vs. 15% standard)
    - ATR-based position sizing (instead of fixed %)
    - Gold Edge specific circuit breaker rules
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, default="Gold Edge Risk")

    # Drawdown limits — Gold Edge allows higher drawdown
    max_drawdown = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.0,
        help_text="Maximum drawdown as percentage — Gold Edge allows 20-40% (default: 30%)",
    )
    max_drawdown_warning = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.0,
        help_text="Drawdown warning threshold — reduce position size (default: 20%)",
    )

    # ATR-based position sizing
    atr_position_sizing = models.BooleanField(
        default=True,
        help_text="Use ATR-based position sizing instead of fixed percentage",
    )
    atr_risk_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.0,
        help_text="ATR multiplier for stop loss distance (default: 2.0)",
    )
    max_risk_per_trade_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.0,
        help_text="Maximum risk per trade as percentage (default: 2%)",
    )
    min_risk_per_trade_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.5,
        help_text="Minimum risk per trade as percentage (default: 0.5%)",
    )

    # Gold Edge circuit breaker rules
    max_consecutive_losses = models.IntegerField(
        default=5,
        help_text="Max consecutive losses before circuit breaker (default: 5)",
    )
    cooldown_minutes_after_circuit_breaker = models.IntegerField(
        default=60,
        help_text="Cooldown period in minutes after circuit breaker triggers (default: 60)",
    )
    max_daily_gold_edge_trades = models.IntegerField(
        default=8,
        help_text="Maximum Gold Edge trades per day (default: 8)",
    )
    min_time_between_trades_minutes = models.IntegerField(
        default=15,
        help_text="Minimum time between Gold Edge trades in minutes (default: 15)",
    )

    # Score thresholds
    min_matrix_score_to_trade = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.60,
        help_text="Minimum Gold Edge matrix score to allow trade (default: 0.60)",
    )

    # Risk-reward requirements
    min_risk_reward_ratio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.5,
        help_text="Minimum risk-reward ratio for Gold Edge trades (default: 1.5)",
    )

    # Correlation and exposure
    max_gold_exposure_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.0,
        help_text="Maximum total gold exposure as % of equity (default: 50%)",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "gold edge risk parameters"

    def __str__(self):
        return f"{self.name} (max DD: {self.max_drawdown}%)"

    def calculate_position_size(
        self,
        equity: float,
        atr_value: float,
        price: float,
    ) -> float:
        """
        Calculate position size based on ATR and risk parameters.

        Args:
            equity: current account equity
            atr_value: current ATR value
            price: current asset price

        Returns:
            Position size in lots (minimum 0.01)
        """
        if atr_value <= 0 or price <= 0:
            return 0.01

        risk_amount = equity * float(self.max_risk_per_trade_pct) / 100.0
        sl_distance = float(self.atr_risk_multiplier) * atr_value

        # P&L per lot per ATR of movement (approximate for gold)
        pip_value_per_lot = 100.0  # $100 per $1 ATR move for 1 lot of gold

        lots = risk_amount / (sl_distance * pip_value_per_lot) if sl_distance > 0 else 0.01
        return max(round(lots, 2), 0.01)

    def check_circuit_breaker(
        self,
        consecutive_losses: int,
        daily_trades: int,
        drawdown_pct: float,
        last_trade_minutes_ago: float,
    ) -> dict:
        """
        Check if Gold Edge circuit breaker should trigger.

        Returns:
            dict with 'triggered' bool and 'reason' string
        """
        if consecutive_losses >= self.max_consecutive_losses:
            return {
                "triggered": True,
                "reason": f"Consecutive losses ({consecutive_losses}) >= max ({self.max_consecutive_losses})",
            }

        if daily_trades >= self.max_daily_gold_edge_trades:
            return {
                "triggered": True,
                "reason": f"Daily trades ({daily_trades}) >= max ({self.max_daily_gold_edge_trades})",
            }

        if drawdown_pct >= float(self.max_drawdown):
            return {
                "triggered": True,
                "reason": f"Drawdown ({drawdown_pct}%) >= max ({self.max_drawdown}%)",
            }

        if last_trade_minutes_ago < self.min_time_between_trades_minutes:
            return {
                "triggered": True,
                "reason": f"Last trade was {last_trade_minutes_ago:.0f}min ago, need {self.min_time_between_trades_minutes}min",
            }

        return {"triggered": False, "reason": "All checks passed"}


class DrawdownMonitor(models.Model):
    """
    Track drawdown and trigger circuit breakers

    Circuit Breakers:
    - Daily loss limit: 2% of equity
    - Max drawdown: 15% of equity (standard) / 20-40% (Gold Edge)
    - Daily target lock: Trading stops at 0.4% daily gain
    - Max daily trades: 10
    - Gold Edge: consecutive loss circuit breaker
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

    # Gold Edge tracking
    gold_edge_consecutive_losses = models.IntegerField(
        default=0,
        help_text="Current consecutive Gold Edge losses",
    )

    # Trigger timestamps
    triggered_at = models.DateTimeField(blank=True, null=True)
    daily_reset_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - DD: {self.drawdown_percent}% - Daily P&L: {self.daily_pnl_percent}%"

    def check_circuit_breaker(self, risk_params, strategy: str = "standard"):
        """Check all circuit breakers and return status.
        
        For Gold Edge strategy, uses the higher drawdown tolerance
        and ATR-adjusted circuit breaker rules.
        """
        alerts = []

        # Determine effective drawdown limit based on strategy
        if strategy == "gold_edge" and getattr(risk_params, "gold_edge_enabled", False):
            effective_max_dd = float(risk_params.gold_edge_max_drawdown)
            effective_daily_loss = float(risk_params.gold_edge_circuit_breaker_loss)
        else:
            effective_max_dd = float(risk_params.max_drawdown)
            effective_daily_loss = float(risk_params.max_daily_loss)

        # Check daily loss limit
        if self.daily_loss_percent >= effective_daily_loss:
            self.is_daily_loss_triggered = True
            self.is_circuit_breaker_triggered = True
            alerts.append((
                "DAILY_LOSS",
                "CRITICAL",
                f"{'Gold Edge ' if strategy == 'gold_edge' else ''}Daily loss limit reached: "
                f"{self.daily_loss_percent}% (limit: {effective_daily_loss}%)",
            ))

        # Check max drawdown
        if self.drawdown_percent >= effective_max_dd:
            self.is_drawdown_triggered = True
            self.is_circuit_breaker_triggered = True
            alerts.append((
                "DRAWDOWN",
                "CRITICAL",
                f"{'Gold Edge ' if strategy == 'gold_edge' else ''}Max drawdown reached: "
                f"{self.drawdown_percent}% (limit: {effective_max_dd}%)",
            ))

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

        # Gold Edge consecutive losses circuit breaker
        if (
            strategy == "gold_edge"
            and getattr(risk_params, "gold_edge_enabled", False)
        ):
            max_consec = getattr(risk_params, "gold_edge_circuit_breaker_consecutive_losses", 4)
            if self.gold_edge_consecutive_losses >= max_consec:
                self.is_circuit_breaker_triggered = True
                alerts.append((
                    "GOLD_EDGE_CONSECUTIVE_LOSSES",
                    "CRITICAL",
                    f"Gold Edge: {self.gold_edge_consecutive_losses} consecutive losing trades "
                    f"— circuit breaker triggered (limit: {max_consec})",
                ))

        if alerts:
            self.triggered_at = self.updated_at
        self.save()

        return alerts

    # ── Tiered Drawdown Recovery Protocols ──────────────────────────────
    #
    # drawdown_pct   Action
    # 5 – 10 %       Reduce size 50 %, max 5 trades / day
    # 10 – 15 %      Reduce size 75 %, max 3 trades / day, Gold Edge only
    # 15 – 20 %      Halt automated trading, manual review required
    # 20 %+          Full stop — no trading allowed
    # ────────────────────────────────────────────────────────────────────

    DRAWDOWN_TIERS = [
        # (lower_pct, upper_pct, size_factor, max_trades, allow_auto, label)
        (5,  10, 0.50, 5,  True,  "Tier 1: reduced size & trades"),
        (10, 15, 0.25, 3,  True,  "Tier 2: Gold Edge only, min size"),
        (15, 20, 0.00, 0,  False, "Tier 3: halt automated — manual review"),
        (20, 999, 0.00, 0, False, "Tier 4: full stop"),
    ]

    def get_drawdown_recovery_tier(self) -> dict:
        """
        Return the current recovery tier based on drawdown percentage.

        Returns:
            dict with keys:
                tier            – int (0 = no tier, 1–4 active)
                label           – str human-readable description
                size_factor     – float multiplier for position sizing (0.0–1.0)
                max_trades      – int max allowed trades/day (0 = halt)
                allow_auto      – bool whether automated trading is allowed
        """
        dd = float(self.drawdown_percent)

        for lower, upper, size_factor, max_trades, allow_auto, label in self.DRAWDOWN_TIERS:
            if lower <= dd < upper:
                return {
                    "tier": self.DRAWDOWN_TIERS.index((lower, upper, size_factor, max_trades, allow_auto, label)) + 1,
                    "label": label,
                    "size_factor": size_factor,
                    "max_trades": max_trades,
                    "allow_auto": allow_auto,
                }

        return {
            "tier": 0,
            "label": "Normal — no recovery restriction",
            "size_factor": 1.0,
            "max_trades": 999,
            "allow_auto": True,
        }

    def apply_drawdown_recovery(self, risk_params, strategy: str = "standard"):
        """
        Apply tiered recovery rules on top of existing circuit breakers.

        Returns a list of alerts similar to check_circuit_breaker().  Call
        *after* check_circuit_breaker() so the standard circuit-breaker
        flags are already set.
        """
        tier = self.get_drawdown_recovery_tier()
        alerts = []

        if tier["tier"] == 0:
            return alerts

        # Tier 1+: Reduce max trades allowed for the day
        if tier["max_trades"] > 0 and self.daily_trades_count >= tier["max_trades"]:
            if not self.is_max_trades_triggered:
                self.is_max_trades_triggered = True
                self.is_circuit_breaker_triggered = True
                alerts.append((
                    "DRAWDOWN_RECOVERY_MAX_TRADES",
                    "HIGH",
                    f"Recovery tier {tier['tier']}: max {tier['max_trades']} trades/day "
                    f"(current: {self.daily_trades_count}). {tier['label']}",
                ))

        # Tier 3+: Halt automated trading
        if not tier["allow_auto"]:
            self.is_circuit_breaker_triggered = True
            alerts.append((
                "DRAWDOWN_RECOVERY_HALT",
                "CRITICAL",
                f"Recovery tier {tier['tier']}: automated trading halted. "
                f"Drawdown: {self.drawdown_percent}%. Manual review required. "
                f"{tier['label']}",
            ))

        # Tier 2+: Restrict to Gold Edge only (if Gold Edge is enabled on params)
        if tier["tier"] >= 2 and strategy != "gold_edge":
            self.is_circuit_breaker_triggered = True
            alerts.append((
                "DRAWDOWN_RECOVERY_GOLD_EDGE_ONLY",
                "HIGH",
                f"Recovery tier {tier['tier']}: non-Gold-Edge trades blocked. "
                f"Drawdown: {self.drawdown_percent}%. {tier['label']}",
            ))

        if alerts:
            self.triggered_at = self.updated_at
        self.save()

        return alerts

    def record_gold_edge_trade(self, pnl: float):
        """Record a Gold Edge trade result and update consecutive loss counter."""
        if pnl < 0:
            self.gold_edge_consecutive_losses += 1
        else:
            self.gold_edge_consecutive_losses = 0
        self.save()

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

    def get_recovery_protocol(self) -> dict:
        """
        Get tiered drawdown recovery protocol based on current drawdown.
        
        Tiers:
        - 5-10%: reduce size 50%, max 5 trades/day
        - 10-15%: reduce size 75%, max 3 trades/day, Gold Edge only
        - 15-20%: halt automated trading, manual review required
        - 20%+: full stop
        """
        dd = float(self.drawdown_percent)
        
        if dd >= 20.0:
            return {
                "tier": "FULL_STOP",
                "severity": "CRITICAL",
                "message": "Drawdown >= 20%. All trading halted. Manual intervention required.",
                "position_size_multiplier": 0.0,
                "max_daily_trades": 0,
                "allow_gold_edge": False,
                "require_manual_review": True,
            }
        elif dd >= 15.0:
            return {
                "tier": "MANUAL_REVIEW",
                "severity": "CRITICAL",
                "message": "Drawdown >= 15%. Automated trading halted. Awaiting manual review.",
                "position_size_multiplier": 0.0,
                "max_daily_trades": 0,
                "allow_gold_edge": False,
                "require_manual_review": True,
            }
        elif dd >= 10.0:
            return {
                "tier": "HIGH_DRAWDOWN",
                "severity": "HIGH",
                "message": "Drawdown >= 10%. Position size reduced 75%, max 3 trades/day, Gold Edge only.",
                "position_size_multiplier": 0.25,
                "max_daily_trades": 3,
                "allow_gold_edge": True,
                "require_manual_review": False,
            }
        elif dd >= 5.0:
            return {
                "tier": "ELEVATED",
                "severity": "MEDIUM",
                "message": "Drawdown >= 5%. Position size reduced 50%, max 5 trades/day.",
                "position_size_multiplier": 0.5,
                "max_daily_trades": 5,
                "allow_gold_edge": True,
                "require_manual_review": False,
            }
        else:
            return {
                "tier": "NORMAL",
                "severity": "LOW",
                "message": "Drawdown within normal parameters.",
                "position_size_multiplier": 1.0,
                "max_daily_trades": None,  # Use default from risk_params
                "allow_gold_edge": True,
                "require_manual_review": False,
            }

    def apply_recovery_protocol(self, risk_params) -> tuple:
        """
        Apply drawdown recovery protocol and return effective settings.
        
        Returns:
            Tuple of (position_size_multiplier, max_daily_trades, allow_gold_edge)
        """
        protocol = self.get_recovery_protocol()
        
        multiplier = protocol["position_size_multiplier"]
        max_trades = protocol["max_daily_trades"]
        allow_gold = protocol["allow_gold_edge"]
        
        # If no specific max trades in protocol, use risk_params default
        if max_trades is None:
            max_trades = risk_params.max_daily_trades
        
        return multiplier, max_trades, allow_gold

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
            "gold_edge_consecutive_losses": self.gold_edge_consecutive_losses,
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


class TradingSettings(models.Model):
    """
    Global trading mode and execution settings.

    Modes:
    - auto: V6 cycle executes trades automatically on MT5
    - semi: V6 generates signals, user approves via dashboard/API
    - manual: Signals are logged only, no execution
    """

    TRADING_MODES = [
        ("auto", "Full Auto — Execute trades automatically"),
        ("semi", "Semi-Auto — Signals require approval"),
        ("manual", "Manual — Signals logged only"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, default="Default Trading Settings")

    trading_mode = models.CharField(
        max_length=10,
        choices=TRADING_MODES,
        default="semi",
        help_text="auto = full auto-trading, semi = requires approval, manual = log only",
    )

    # Execution parameters
    max_slippage_pips = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.5,
        help_text="Maximum allowed slippage in pips before rejecting a trade",
    )
    max_spread_pips = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.5,
        help_text="Maximum allowed spread in pips before rejecting a trade",
    )
    min_confidence = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.65,
        help_text="Minimum signal confidence to consider executing (0.0-1.0)",
    )

    # Active symbols — all 28 from MarketScanner.DEFAULT_SYMBOLS
    active_symbols = models.TextField(
        default="EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,NZDUSD,EURGBP,EURJPY,GBPJPY,AUDJPY,EURAUD,EURCHF,GBPCAD,USDTRY,USDZAR,USDMXN,USDCNH,XAUUSD,XAGUSD,XAUEUR,BTCUSD,ETHUSD,SOLUSD,US30,US500,NAS100,GER40",
        help_text="Comma-separated list of symbols to trade (all 28 MarketScanner symbols)",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Trading Settings"
        verbose_name_plural = "Trading Settings"

    def __str__(self):
        return f"{self.name} — Mode: {self.get_trading_mode_display()}"

    def get_symbol_list(self):
        """Return active symbols as a list."""
        return [s.strip() for s in self.active_symbols.split(",") if s.strip()]

    @classmethod
    def get_active(cls):
        """Get or create the active trading settings singleton."""
        settings, _ = cls.objects.get_or_create(
            is_active=True,
            defaults={"name": "Default Trading Settings"},
        )
        return settings
