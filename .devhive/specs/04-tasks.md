# Tasks — V6.5 Profit Target Unification

## Backend Tasks
- [ ] **1. Create `backend/ml/enhancements/profit_target_manager.py`**
  - Implement `ProfitTargetManager` class
  - Dynamic daily target calculation (win rate, equity, regime, drawdown)
  - Weekly/monthly/annual target compounding
  - `manage_targets()` entry point for V6.5 Phase 16
  - Integration with RiskParameter and DrawdownMonitor models

- [ ] **2. Modify `backend/ml/v65_orchestrator.py`**
  - Add Phase 16: Profit Target Management in `run_trading_cycle()`
  - Add `_phase16_profit_targets()` method
  - Import and lazy-load ProfitTargetManager
  - Return `trading_allowed` status from Phase 16
  - Update phase count in `get_status()` from 22 to 23

- [ ] **3. Modify `backend/risk_management/models.py`**
  - Add `weekly_target` field to RiskParameter (DecimalField, default=1.0)
  - Update class docstring to indicate V6.5-managed targets
  - Add help_text for weekly_target

- [ ] **4. Modify `backend/risk_management/daily_target.py`**
  - In `DailyTargetLock.__init__()`: accept optional `v65_target` parameter
  - In `check_daily_status()`: if V6.5 target available, use it instead of profile
  - Add `set_v65_target()` method to receive V6.5-determined target
  - Keep existing profile logic as fallback

- [ ] **5. Modify `backend/config/settings_production.py`**
  - Update TRADING_CONFIG to include ALL profit targets
  - Set `TARGET_DAILY_GROWTH: 0.14`, `TARGET_WEEKLY_GROWTH: 1.0`
  - Set `TARGET_MONTHLY_GROWTH: 4.2`, `TARGET_ANNUAL_GROWTH: 50.0`
  - Align annual target from 0.40 to 50.0

- [ ] **6. Modify `backend/config/settings.py`**
  - Same TRADING_CONFIG updates as settings_production.py

- [ ] **7. Modify `backend/config/settings_prod.py`**
  - Same TRADING_CONFIG updates as settings_production.py

- [ ] **8. Modify `backend/config/tasks.py`**
  - In `run_v6_trading_cycle()`: after orchestrator.run_trading_cycle(), check profit target status
  - In `monitor_drawdown()`: delegate target logic to V6.5's ProfitTargetManager
  - Add `v65_manage_profit_targets` shared task

- [ ] **9. Modify `backend/config/celery_schedule.py`**
  - Add `v65-manage-profit-targets` to STATIC_TASKS
  - Schedule: every 60 seconds (same as trading cycle)

## Data Tasks
- [ ] **10. Create Django migration for weekly_target field**
  - `python manage.py makemigrations risk_management`
  - Verify migration applies cleanly

## Documentation Tasks
- [ ] **11. Update backend/ml/v65_orchestrator.py docstring**
  - Add Phase 16 to the phases list at top of file

## Release Tasks
- [ ] **12. Version bump and changelog**
  - Update version to reflect profit target unification
