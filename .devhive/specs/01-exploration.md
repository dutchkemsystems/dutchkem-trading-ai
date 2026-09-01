# Exploration — V6.5 Profit Target Unification

## Existing Codebase Analysis

### File: `backend/ml/v65_orchestrator.py`
- **Current State**: 15 phases (0-15), no profit target management
- **Pipeline**: Scan → AI → Sentiment → News → OrderFlow → Pattern → MultiTF → Signal → Risk → SL → TP → Diversify → Execute → Exit → Learn
- **Gap**: No phase reads or sets profit targets. Risk management (Phase 9) only checks position sizing, not account-level targets.

### File: `backend/risk_management/models.py`
- **RiskParameter**: Has `daily_growth_target=0.14`, `daily_target_lock=0.4`, `target_monthly_growth=4.2`, `target_annual_growth=50.0`
- **Gap**: No `weekly_target` field. Three conflicting daily target values (0.14, 0.4, and DailyTargetLock's 0.8/1.45/2.2).
- **DrawdownMonitor**: Has `is_daily_target_triggered` but it's set by DailyTargetLock, not V6.5.

### File: `backend/risk_management/daily_target.py`
- **DailyTargetLock**: Standalone class with hardcoded profiles (conservative=0.80%, moderate=1.45%, aggressive=2.20%)
- **Gap**: Not connected to V6.5 trading cycle. Uses hardcoded profiles instead of dynamic determination.

### File: `backend/config/settings_production.py`
- **TRADING_CONFIG**: Contains only `MAX_DRAWDOWN`, `MAX_DAILY_LOSS`, `MAX_POSITION_SIZE`, `MAX_OPEN_POSITIONS`, `MAX_CORRELATION`, `MIN_RISK_REWARD_RATIO`, `TARGET_ANNUAL_GROWTH=0.40`
- **Gap**: Dead code — no module imports or reads TRADING_CONFIG. Annual target (0.40) conflicts with RiskParameter (50.0). No daily/weekly/monthly targets.

### File: `backend/config/tasks.py`
- **run_v6_trading_cycle**: Calls orchestrator.run_trading_cycle() but never manages profit targets
- **monitor_drawdown**: Standalone task, doesn't delegate to V6.5
- **Gap**: No profit target management in the trading cycle

### File: `backend/config/celery_schedule.py`
- **Static tasks**: monitor-drawdown, reset-daily-counters, run-v6-trading-cycle, run-v6-optimization
- **Gap**: No profit target management task

## Dependency Graph
```
V65TradingOrchestrator (Phase 16)
  └── ProfitTargetManager (NEW)
        ├── Reads RiskParameter (weekly_target, daily targets)
        ├── Reads DrawdownMonitor (current drawdown)
        ├── Reads Trade history (win rate)
        ├── Sets DrawdownMonitor.is_daily_target_triggered
        └── Updates RiskParameter targets dynamically

DailyTargetLock → defers to ProfitTargetManager
TRADING_CONFIG → referenced by V6.5 for defaults
monitor_drawdown → delegates target logic to V6.5
```

## Risk Assessment
- **Low Risk**: Adding new Phase 16 to orchestrator (additive, no existing logic changed)
- **Low Risk**: Adding weekly_target field (new field, no migration conflict)
- **Medium Risk**: Modifying DailyTargetLock to defer (behavioral change, but correct)
- **Low Risk**: Updating TRADING_CONFIG (dead code becoming live)
- **Low Risk**: Adding Celery task (additive)
