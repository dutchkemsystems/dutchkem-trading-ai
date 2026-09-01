# Product Requirements Document — V6.5 Profit Target Unification

## Overview
Unify ALL profit target determination under V6.5 as the sole authoritative system. Currently, profit targets are determined by 3 conflicting systems (RiskParameter model, DailyTargetLock, TRADING_CONFIG), none of which are connected to V6.5. This fix makes V6.5 the COMPULSORY/DEFAULT method for determining daily, weekly, monthly, and annual profit targets.

## Current Problems
1. V6.5 does NOT determine profit targets — it only generates signals and executes trades
2. Profit targets are determined by risk_management app independently (3 conflicting systems)
3. TRADING_CONFIG in settings is dead code — never used by any module
4. DailyTargetLock (0.80%/1.45%/2.20%) is disconnected from the trading cycle
5. No weekly profit target exists anywhere
6. Three different daily target values coexist (0.14%, 0.40%, 0.80%/1.45%/2.20%)
7. V6.5 never reads or sets any profit target values

## Goals
1. V6.5 MUST be the ONLY system that determines profit targets
2. All other systems (risk_management, DailyTargetLock) must defer to V6.5
3. Weekly profit target MUST be added
4. TRADING_CONFIG must actually be used
5. No conflicting target values
6. V6.5 must dynamically adjust targets based on performance

## Success Criteria
- V6.5 orchestrator has a new Phase 16: Profit Target Management
- `ProfitTargetManager` class in `ml/enhancements/profit_target_manager.py` handles all target logic
- RiskParameter model gains `weekly_target` field
- DailyTargetLock defers to V6.5 for target determination
- TRADING_CONFIG includes ALL profit targets and is referenced by V6.5
- Celery beat schedule includes `v65-manage-profit-targets` task
- `run_v6_trading_cycle` calls profit target management
- `monitor_drawdown` delegates to V6.5 for target determination

## Constraints
- Must maintain backward compatibility with existing database migrations
- Must not break existing trading cycle execution
- Must work with both local dev and production (Render)
- All targets must be dynamically adjustable by V6.5

## Architecture
### New Component: ProfitTargetManager
- Location: `backend/ml/enhancements/profit_target_manager.py`
- V6.5 determines daily target dynamically based on:
  - Recent win rate (last 20 trades)
  - Current equity
  - Market regime (from V6.5's regime detection)
  - Current drawdown level
- Weekly target = compounding of daily targets
- Monthly target = compounding of weekly targets
- Annual target = compounding of monthly targets
- All targets enforced through V6.5's pipeline

### Modified Components
1. `backend/ml/v65_orchestrator.py` — Add Phase 16
2. `backend/risk_management/models.py` — Add weekly_target field
3. `backend/risk_management/daily_target.py` — Defer to V6.5
4. `backend/config/settings_production.py` — Update TRADING_CONFIG
5. `backend/config/tasks.py` — Add profit target management call
6. `backend/config/celery_schedule.py` — Add beat schedule entry
