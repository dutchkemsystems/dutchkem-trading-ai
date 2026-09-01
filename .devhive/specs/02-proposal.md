# Proposal — V6.5 Profit Target Unification

## Summary
Create a unified profit target system where V6.5 is the sole authority for determining daily, weekly, monthly, and annual profit targets. All other systems defer to V6.5.

## Changes

### 1. NEW: `backend/ml/enhancements/profit_target_manager.py`
- `ProfitTargetManager` class with dynamic target calculation
- Daily target based on: win rate, equity, market regime, drawdown
- Weekly/monthly/annual targets via compounding
- Integration point for V6.5 Phase 16

### 2. MODIFY: `backend/ml/v65_orchestrator.py`
- Add Phase 16: Profit Target Management
- Call `ProfitTargetManager.manage_targets()` every cycle
- Pass profit target status to risk management phase

### 3. MODIFY: `backend/risk_management/models.py`
- Add `weekly_target` field to RiskParameter (default: 1.0%)
- Update docstring to indicate V6.5-managed targets

### 4. MODIFY: `backend/risk_management/daily_target.py`
- DailyTargetLock delegates to V6.5's ProfitTargetManager
- Remove hardcoded profiles
- Use V6.5-determined profile dynamically

### 5. MODIFY: `backend/config/settings_production.py`
- Update TRADING_CONFIG with ALL profit targets
- Align annual target to 50% (matching RiskParameter)
- Add daily, weekly, monthly targets

### 6. MODIFY: `backend/config/tasks.py`
- In `run_v6_trading_cycle`: call profit target management
- In `monitor_drawdown`: delegate to V6.5 for target determination

### 7. MODIFY: `backend/config/celery_schedule.py`
- Add `v65-manage-profit-targets` task (every 60 seconds)

## Acceptance Criteria
- [ ] V6.5 orchestrator has Phase 16 that manages profit targets
- [ ] ProfitTargetManager calculates dynamic daily targets
- [ ] RiskParameter has weekly_target field
- [ ] DailyTargetLock defers to V6.5
- [ ] TRADING_CONFIG is actually used by V6.5
- [ ] Celery beat includes profit target task
- [ ] No conflicting target values exist
- [ ] All existing tests still pass

## Out of Scope
- Frontend UI changes for profit target display
- Database migration for existing data (new field has default)
- Changes to Gold Edge specific logic (already handled separately)
