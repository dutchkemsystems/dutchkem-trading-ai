# Fix Proposal — Dutchkem Trading AI

## Date: 2026-08-28

---

## 1. Fix Categories

### Category A: Critical Blockers (Immediate)

| ID | Fix | Priority | Effort |
|----|-----|----------|--------|
| A1 | Fix root config conflict | P0 | Low |
| A2 | Generate all missing migrations | P0 | Medium |
| A3 | Fix analytics field name bugs | P0 | Low |

### Category B: Security (Immediate)

| ID | Fix | Priority | Effort |
|----|-----|----------|--------|
| B1 | Remove hardcoded secrets | P0 | Low |
| B2 | Set RATELIMIT_FAIL_OPEN = False | P0 | Low |
| B3 | Enforce webhook signature verification | P0 | Low |

### Category C: Backend Quality (Short-term)

| ID | Fix | Priority | Effort |
|----|-----|----------|--------|
| C1 | Add select_related for N+1 queries | P1 | Low |
| C2 | Add analytics caching models | P1 | Medium |
| C3 | Complete notification service | P1 | Medium |
| C4 | Add Celery periodic task config | P1 | Low |
| C5 | Create seed data management command | P1 | Medium |

### Category D: Frontend (Medium-term)

| ID | Fix | Priority | Effort |
|----|-----|----------|--------|
| D1 | Add missing Redux slices | P2 | Medium |
| D2 | Complete page implementations | P2 | High |

---

## 2. Detailed Fix Specifications

### A1: Fix Root Config Conflict
- Remove or rename root `config/settings.py`
- Update root `manage.py` to point to correct settings OR
- Make root config import from backend config

**Decision**: Keep root config as a thin wrapper that imports from backend config

### A2: Generate Missing Migrations
Run `python manage.py makemigrations` for each app:
- accounts
- risk_management
- payments
- expert_advisors
- mcp_integration
- market_data
- notifications
- analytics (after adding models)

### A3: Fix Analytics Field Name Bugs
Replace in `analytics/views.py`:
- `close_time` → `closed_at`
- `pnl` → `profit_loss`
- Remove `status="ACTIVE"` filter (Signal has no status field)

### B1: Remove Hardcoded Secrets
In `backend/config/settings.py`:
- Change DB_PASSWORD default to empty string
- Change SECRET_KEY default to raise error if not set

### B2: Set RATELIMIT_FAIL_OPEN = False
In `backend/config/settings.py`:
- Change `RATELIMIT_FAIL_OPEN = True` to `RATELIMIT_FAIL_OPEN = False`

### B3: Enforce Webhook Signature
In `payments/gateways/korapay.py`:
- Return False instead of True when secret not set

### C1: Add select_related
In `trading/views.py` TradeListView:
- Add `.select_related('symbol', 'timeframe', 'signal', 'expert_advisor')`

### C2: Add Analytics Caching Models
Create `analytics/models.py` with:
- CachedTradeSummary
- CachedDailyPerformance
- CachedSymbolBreakdown

### C3: Complete Notification Service
In `notifications/`:
- Add email sending via Django email backend
- Add SMS via Africa's Talking or Twilio
- Add push via FCM

### C4: Add Celery Periodic Tasks
Verify and update `config/celery_schedule.py`

### C5: Create Seed Data Command
Create `management/commands/seed_data.py` with:
- Default symbols (EURUSD, GBPUSD, etc.)
- Timeframes (M5, M15, M30, H1, H2, H4)
- Indicator categories and indicators
- Default risk parameters
