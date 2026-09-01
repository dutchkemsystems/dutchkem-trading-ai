"""
V6.5 Unified Profit Target Manager
===================================

This is the COMPULSORY and ONLY system for determining ALL profit targets.
Every other system (DailyTargetLock, RiskParameter, TRADING_CONFIG) must
defer to this manager.

V6.5 dynamically determines targets based on:
  - Recent win rate (last N trades)
  - Current equity and drawdown level
  - Market regime (TRENDING, RANGING, VOLATILE, BREAKOUT)
  - Performance history (daily/weekly/monthly compounding)

Target Hierarchy (all computed from daily base):
  Daily Target   = f(win_rate, equity, regime, drawdown)
  Weekly Target  = compounding of daily targets (5 trading days)
  Monthly Target = compounding of weekly targets (4 weeks)
  Annual Target  = compounding of monthly targets (12 months)

Integration:
  - Called as Phase 16 in V6.5 orchestrator
  - Sets is_daily_target_triggered on DrawdownMonitor
  - Replaces DailyTargetLock, RiskParameter hardcoded targets
  - TRADING_CONFIG targets are overridden by V6.5 computed targets
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger("ml.v65.profit_target")


class ProfitTargetManager:
    """
    V6.5 Unified Profit Target Manager.

    Determines all profit targets dynamically based on real performance.
    """

    # ── Regime-based scaling factors ──────────────────────────────────
    # These multiply the base daily target to adjust for market conditions.
    REGIME_SCALERS = {
        "TRENDING": 1.2,    # Trending markets allow higher targets
        "BREAKOUT": 1.1,    # Breakout slightly elevated
        "RANGING": 0.7,     # Ranging markets: be conservative
        "VOLATILE": 0.8,    # Volatile: slightly reduce to manage risk
        "NORMAL": 1.0,      # Baseline
        "unknown": 1.0,     # Fallback
    }

    # ── Drawdown-based scaling factors ────────────────────────────────
    # As drawdown increases, targets are reduced to protect capital.
    DRAWDOWN_SCALERS = [
        # (drawdown_pct_lower, drawdown_pct_upper, scale_factor)
        (0.0,  5.0,  1.0),    # Normal: full target
        (5.0,  10.0, 0.6),    # Elevated drawdown: reduce 40%
        (10.0, 15.0, 0.3),    # High drawdown: reduce 70%
        (15.0, 20.0, 0.0),    # Critical: no target (halt)
        (20.0, 100.0, 0.0),   # Full stop
    ]

    # ── Win rate based base daily target (%) ──────────────────────────
    # Maps win rate ranges to base daily target percentages.
    WINRATE_TARGET_MAP = [
        # (win_rate_lower, win_rate_upper, base_daily_target_pct)
        (0.0,  30.0, 0.05),   # Very poor win rate: minimal target
        (30.0, 40.0, 0.08),   # Below average
        (40.0, 50.0, 0.12),   # Average
        (50.0, 55.0, 0.15),   # Above average (default baseline)
        (55.0, 60.0, 0.18),   # Good
        (60.0, 70.0, 0.22),   # Very good
        (70.0, 100.0, 0.25),  # Excellent
    ]

    # ── Equity-based scaling (accounts with more equity get slight boost) ──
    EQUITY_BASELINE = 10000.0  # Baseline equity for scaling

    # ── Minimum and maximum daily targets (hard bounds) ───────────────
    MIN_DAILY_TARGET_PCT = 0.03   # Never target less than 0.03%/day
    MAX_DAILY_TARGET_PCT = 0.50   # Never target more than 0.50%/day

    # Trading days per period
    TRADING_DAYS_PER_WEEK = 5
    TRADING_WEEKS_PER_MONTH = 4
    TRADING_MONTHS_PER_YEAR = 12

    def __init__(self):
        self._cached_targets: Optional[Dict[str, Any]] = None
        self._cache_date: Optional[date] = None

    # ── Main entry point ──────────────────────────────────────────────

    def compute_targets(
        self,
        current_equity: float,
        peak_equity: float,
        recent_trades: Optional[list] = None,
        regime: str = "NORMAL",
        v65_orchestrator=None,
    ) -> Dict[str, Any]:
        """
        Compute all profit targets dynamically based on V6.5 performance data.

        Args:
            current_equity: Current account equity
            peak_equity: Peak equity (for drawdown calc)
            recent_trades: List of recent trade dicts with 'pnl' key
            regime: Current market regime from V6.5 Phase 2
            v65_orchestrator: Reference to V6.5 orchestrator for extra data

        Returns:
            Dict with daily/weekly/monthly/annual targets and metadata
        """
        today = date.today()

        # Return cached if same day (targets reset daily)
        if self._cached_targets and self._cache_date == today:
            return self._cached_targets

        # ── 1. Calculate current drawdown ─────────────────────────────
        drawdown_pct = 0.0
        if peak_equity > 0:
            drawdown_pct = max(0.0, ((peak_equity - current_equity) / peak_equity) * 100.0)

        # ── 2. Calculate recent win rate ──────────────────────────────
        win_rate = self._calculate_win_rate(recent_trades)

        # ── 3. Get base daily target from win rate ────────────────────
        base_daily_pct = self._winrate_to_target(win_rate)

        # ── 4. Apply regime scaling ───────────────────────────────────
        regime_scale = self.REGIME_SCALERS.get(regime, 1.0)
        scaled_daily_pct = base_daily_pct * regime_scale

        # ── 5. Apply drawdown scaling ─────────────────────────────────
        dd_scale = self._drawdown_scale(drawdown_pct)
        scaled_daily_pct *= dd_scale

        # ── 6. Apply equity scaling (subtle) ──────────────────────────
        equity_scale = self._equity_scale(current_equity)
        scaled_daily_pct *= equity_scale

        # ── 7. Enforce hard bounds ────────────────────────────────────
        daily_pct = max(self.MIN_DAILY_TARGET_PCT, min(self.MAX_DAILY_TARGET_PCT, scaled_daily_pct))

        # ── 8. Compute compounded period targets ──────────────────────
        weekly_pct = self._compound_target(daily_pct, self.TRADING_DAYS_PER_WEEK)
        monthly_pct = self._compound_target(weekly_pct, self.TRADING_WEEKS_PER_MONTH)
        annual_pct = self._compound_target(monthly_pct, self.TRADING_MONTHS_PER_YEAR)

        # ── 9. Compute absolute amounts ───────────────────────────────
        daily_amount = current_equity * (Decimal(str(daily_pct)) / 100)
        weekly_amount = current_equity * (Decimal(str(weekly_pct)) / 100)
        monthly_amount = current_equity * (Decimal(str(monthly_pct)) / 100)
        annual_amount = current_equity * (Decimal(str(annual_pct)) / 100)

        # ── 10. Determine target profile name ─────────────────────────
        profile = self._classify_profile(daily_pct)

        result = {
            "timestamp": today.isoformat(),
            "version": "6.5",
            "method": "V65_DYNAMIC",
            "profile": profile,
            "inputs": {
                "current_equity": round(current_equity, 2),
                "peak_equity": round(peak_equity, 2),
                "drawdown_pct": round(drawdown_pct, 2),
                "win_rate": round(win_rate, 1),
                "regime": regime,
                "regime_scale": regime_scale,
                "drawdown_scale": dd_scale,
                "equity_scale": round(equity_scale, 4),
            },
            "targets": {
                "daily_pct": round(daily_pct, 4),
                "daily_amount": round(float(daily_amount), 2),
                "weekly_pct": round(weekly_pct, 4),
                "weekly_amount": round(float(weekly_amount), 2),
                "monthly_pct": round(monthly_pct, 2),
                "monthly_amount": round(float(monthly_amount), 2),
                "annual_pct": round(annual_pct, 2),
                "annual_amount": round(float(annual_amount), 2),
            },
            "source": "V6.5_ORCHESTRATOR",
        }

        self._cached_targets = result
        self._cache_date = today

        logger.info(
            "V6.5 profit targets computed: daily=%.4f%%, weekly=%.4f%%, "
            "monthly=%.2f%%, annual=%.2f%% (regime=%s, dd=%.1f%%, wr=%.0f%%)",
            daily_pct, weekly_pct, monthly_pct, annual_pct,
            regime, drawdown_pct, win_rate,
        )

        return result

    # ── Internal methods ──────────────────────────────────────────────

    def _calculate_win_rate(self, recent_trades: Optional[list]) -> float:
        """Calculate win rate from recent trades (last 50 trades)."""
        if not recent_trades:
            return 50.0  # Default assumption when no data

        # Take last 50 trades for recency
        trades = recent_trades[-50:] if len(recent_trades) > 50 else recent_trades
        if not trades:
            return 50.0

        wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
        return (wins / len(trades)) * 100.0

    def _winrate_to_target(self, win_rate: float) -> float:
        """Map win rate to base daily target percentage."""
        for lower, upper, target in self.WINRATE_TARGET_MAP:
            if lower <= win_rate < upper:
                return target
        # Fallback for very high win rates
        return self.WINRATE_TARGET_MAP[-1][2]

    def _drawdown_scale(self, drawdown_pct: float) -> float:
        """Return drawdown-based scaling factor."""
        for lower, upper, scale in self.DRAWDOWN_SCALERS:
            if lower <= drawdown_pct < upper:
                return scale
        return 0.0  # Beyond all tiers: full stop

    def _equity_scale(self, equity: float) -> float:
        """Subtle equity-based scaling. Larger accounts get slight boost."""
        if equity <= 0:
            return 1.0
        # Logarithmic scaling around baseline: range roughly 0.9 - 1.1
        import math
        scale = 1.0 + (math.log(equity / self.EQUITY_BASELINE) * 0.05)
        return max(0.9, min(1.1, scale))

    def _compound_target(self, period_pct: float, periods: int) -> float:
        """
        Compound a target over N periods.
        Example: daily 0.15% compounded over 5 days = weekly target.
        Formula: ((1 + pct/100)^periods - 1) * 100
        """
        return ((1 + period_pct / 100.0) ** periods - 1) * 100.0

    def _classify_profile(self, daily_pct: float) -> str:
        """Classify the computed target into a profile name."""
        if daily_pct <= 0.08:
            return "conservative"
        elif daily_pct <= 0.18:
            return "moderate"
        else:
            return "aggressive"

    # ── Integration methods ───────────────────────────────────────────

    def enforce_targets_on_drawdown_monitor(
        self,
        daily_pnl_pct: float,
        drawdown_monitor,
    ) -> Dict[str, Any]:
        """
        Update DrawdownMonitor with V6.5 computed target.

        Args:
            daily_pnl_pct: Today's P&L as percentage
            drawdown_monitor: DrawdownMonitor model instance

        Returns:
            Dict with enforcement action
        """
        # Get the V6.5 daily target from last computed targets
        daily_target = self._get_current_daily_target()

        # Check if target is reached
        is_target_reached = daily_pnl_pct >= daily_target

        # Update DrawdownMonitor
        drawdown_monitor.is_daily_target_triggered = is_target_reached
        drawdown_monitor.save(update_fields=["is_daily_target_triggered"])

        action = "halt" if is_target_reached else "continue"
        logger.info(
            "V6.5 target enforcement: pnl=%.4f%%, target=%.4f%%, action=%s",
            daily_pnl_pct, daily_target, action,
        )

        return {
            "action": action,
            "daily_pnl_pct": round(daily_pnl_pct, 4),
            "daily_target_pct": round(daily_target, 4),
            "source": "V6.5_ORCHESTRATOR",
        }

    def _get_current_daily_target(self) -> float:
        """Get today's daily target. Returns cached or default."""
        if self._cached_targets and self._cache_date == date.today():
            return self._cached_targets["targets"]["daily_pct"]
        return 0.15  # Default conservative fallback

    def should_allow_new_trade(
        self,
        daily_pnl_pct: float,
        drawdown_pct: float,
        daily_trades_count: int,
        max_daily_trades: int = 10,
    ) -> Dict[str, Any]:
        """
        V6.5 decides whether a new trade is allowed based on profit targets.

        Returns:
            Dict with 'allowed' bool and reason
        """
        daily_target = self._get_current_daily_target()
        daily_loss_limit = 2.0  # 2% daily loss limit

        # Check daily target reached
        if daily_pnl_pct >= daily_target:
            return {
                "allowed": False,
                "reason": "DAILY_TARGET_REACHED",
                "message": f"V6.5 daily target {daily_target:.4f}% reached (P&L: {daily_pnl_pct:.4f}%)",
                "source": "V6.5_ORCHESTRATOR",
            }

        # Check daily loss limit
        if daily_pnl_pct <= -daily_loss_limit:
            return {
                "allowed": False,
                "reason": "DAILY_LOSS_LIMIT",
                "message": f"V6.5 daily loss limit -{daily_loss_limit}% reached (P&L: {daily_pnl_pct:.4f}%)",
                "source": "V6.5_ORCHESTRATOR",
            }

        # Check max trades
        if daily_trades_count >= max_daily_trades:
            return {
                "allowed": False,
                "reason": "MAX_DAILY_TRADES",
                "message": f"Max daily trades {max_daily_trades} reached",
                "source": "V6.5_ORCHESTRATOR",
            }

        # Check drawdown
        dd_scale = self._drawdown_scale(drawdown_pct)
        if dd_scale == 0.0:
            return {
                "allowed": False,
                "reason": "DRAWDOWN_HALT",
                "message": f"V6.5 halted trading: drawdown {drawdown_pct:.1f}% exceeds safe threshold",
                "source": "V6.5_ORCHESTRATOR",
            }

        return {
            "allowed": True,
            "reason": "OK",
            "daily_target": round(daily_target, 4),
            "remaining_to_target": round(daily_target - daily_pnl_pct, 4),
            "source": "V6.5_ORCHESTRATOR",
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the profit target manager."""
        targets = self._cached_targets
        return {
            "initialized": True,
            "version": "6.5",
            "cached_date": self._cache_date.isoformat() if self._cache_date else None,
            "current_targets": targets.get("targets") if targets else None,
            "source": "V6.5_ORCHESTRATOR",
        }
