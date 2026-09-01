# Architecture — V6.5 Profit Target Unification

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    V6.5 Trading Orchestrator                 │
│  Phase 0-15 (existing)  │  Phase 16: Profit Target Mgmt    │
└──────────┬──────────────┴──────────┬───────────────────────┘
           │                         │
           ▼                         ▼
┌──────────────────┐    ┌─────────────────────────┐
│  Risk Management │    │  ProfitTargetManager     │
│  (Phase 9)       │    │  (NEW - ml/enhancements) │
└──────────────────┘    └─────────┬───────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌──────────┐  ┌──────────┐  ┌──────────┐
            │RiskParam │  │Drawdown  │  │ Trade    │
            │(weekly,  │  │Monitor   │  │ History  │
            │ daily,   │  │(current  │  │(win rate)│
            │ monthly, │  │ drawdown)│  │          │
            │ annual)  │  │          │  │          │
            └──────────┘  └──────────┘  └──────────┘
```

## Component Design

### ProfitTargetManager (NEW)
```python
class ProfitTargetManager:
    """V6.5 profit target determination engine."""
    
    def determine_daily_target(
        self, 
        win_rate: float, 
        current_equity: float, 
        market_regime: str, 
        current_drawdown: float
    ) -> Decimal:
        """
        Dynamic daily target calculation:
        - Base: 0.14% (conservative)
        - Win rate bonus: +0.01% per 5% above 50% win rate
        - Regime adjustment: bullish +0.05%, bearish -0.05%
        - Drawdown penalty: -0.02% per 5% drawdown
        - Floor: 0.05%, Ceiling: 0.50%
        """
    
    def determine_weekly_target(self, daily_target: float) -> Decimal:
        """Weekly = compounding of 5 trading days."""
    
    def determine_monthly_target(self, weekly_target: float) -> Decimal:
        """Monthly = compounding of ~4.3 weeks."""
    
    def determine_annual_target(self, monthly_target: float) -> Decimal:
        """Annual = compounding of 12 months."""
    
    def manage_targets(self, orchestrator_state: dict) -> dict:
        """Main entry point called by V6.5 Phase 16."""
```

### V6.5 Phase 16 Integration
```python
# In V65TradingOrchestrator.run_trading_cycle():
# ── PHASE 16: Profit Target Management ──
with _PhaseTimer("phase16_profit_targets_ms", result["timings"]):
    target_result = self._phase16_profit_targets(market_data)
    result["phases"]["profit_targets"] = target_result

if not target_result.get("trading_allowed"):
    result["status"] = "TARGET_REACHED"
    self._record_cycle(cycle_start, result)
    return result
```

### DailyTargetLock Delegation
```python
# Modified DailyTargetLock.check_daily_status():
def check_daily_status(self, user):
    # Delegate to V6.5's ProfitTargetManager
    from ml.enhancements.profit_target_manager import ProfitTargetManager
    manager = ProfitTargetManager()
    v65_target = manager.get_current_daily_target()
    
    # Use V6.5 target instead of hardcoded profile
    self._target_pct = v65_target
    # ... rest of existing logic
```

## Data Flow

### Per-Cycle Flow
1. V6.5 Phase 16 calls `ProfitTargetManager.manage_targets()`
2. Manager reads: win rate, equity, regime, drawdown
3. Manager calculates dynamic daily/weekly/monthly/annual targets
4. Manager updates RiskParameter with new targets
5. Manager checks if daily target is reached → sets `DrawdownMonitor.is_daily_target_triggered`
6. Phase 16 returns `trading_allowed: bool`
7. If not allowed, cycle exits with `TARGET_REACHED` status

### Target Compounding Formula
```
weekly = (1 + daily)^5 - 1
monthly = (1 + weekly)^4.33 - 1
annual = (1 + monthly)^12 - 1
```

## Database Changes
- `RiskParameter`: Add `weekly_target` field (DecimalField, default=1.0)
- No other schema changes needed (DrawdownMonitor already has `is_daily_target_triggered`)
