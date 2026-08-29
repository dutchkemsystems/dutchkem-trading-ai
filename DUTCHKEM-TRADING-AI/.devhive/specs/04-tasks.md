# Task Planner — Dutchkem Trading AI

## Date: 2026-08-28

---

## Task Categories

### Category A: Critical Blockers

| Task | File(s) | Description | Status |
|------|---------|-------------|--------|
| A1.1 | `config/settings.py` | Make root settings import from backend config | TODO |
| A1.2 | `manage.py` (root) | Ensure root manage.py uses correct settings | TODO |
| A2.1 | `accounts/migrations/` | Generate accounts migrations | TODO |
| A2.2 | `risk_management/migrations/` | Generate risk_management migrations | TODO |
| A2.3 | `payments/migrations/` | Generate payments migrations | TODO |
| A2.4 | `expert_advisors/migrations/` | Generate expert_advisors migrations | TODO |
| A2.5 | `mcp_integration/migrations/` | Generate mcp_integration migrations | TODO |
| A2.6 | `market_data/migrations/` | Generate market_data migrations | TODO |
| A2.7 | `notifications/migrations/` | Generate notifications migrations | TODO |
| A2.8 | `analytics/migrations/` | Generate analytics migrations (after adding models) | TODO |
| A3.1 | `analytics/views.py` | Fix `close_time` → `closed_at` | TODO |
| A3.2 | `analytics/views.py` | Fix `pnl` → `profit_loss` | TODO |
| A3.3 | `analytics/views.py` | Remove invalid `status="ACTIVE"` filter | TODO |

### Category B: Security

| Task | File(s) | Description | Status |
|------|---------|-------------|--------|
| B1.1 | `config/settings.py` | Remove hardcoded DB_PASSWORD default | TODO |
| B1.2 | `config/settings.py` | Remove hardcoded SECRET_KEY default | TODO |
| B2.1 | `config/settings.py` | Set RATELIMIT_FAIL_OPEN = False | TODO |
| B3.1 | `payments/gateways/korapay.py` | Reject webhooks when no secret configured | TODO |

### Category C: Backend Quality

| Task | File(s) | Description | Status |
|------|---------|-------------|--------|
| C1.1 | `trading/views.py` | Add select_related to TradeListView | TODO |
| C1.2 | `trading/views.py` | Add select_related to TradeDetailView | TODO |
| C2.1 | `analytics/models.py` | Create analytics caching models | TODO |
| C2.2 | `analytics/admin.py` | Register analytics models in admin | TODO |
| C3.1 | `notifications/services.py` | Create notification service | TODO |
| C4.1 | `config/celery_schedule.py` | Verify and update periodic tasks | TODO |
| C5.1 | `management/commands/seed_data.py` | Create seed data command | TODO |

### Category D: Frontend

| Task | File(s) | Description | Status |
|------|---------|-------------|--------|
| D1.1 | `features/payments/paymentsSlice.js` | Create payments Redux slice | TODO |
| D1.2 | `features/eas/easSlice.js` | Create EAs Redux slice | TODO |
| D1.3 | `features/analytics/analyticsSlice.js` | Create analytics Redux slice | TODO |
| D1.4 | `features/notifications/notificationsSlice.js` | Create notifications slice | TODO |
| D1.5 | `features/settings/settingsSlice.js` | Create settings slice | TODO |
| D1.6 | `store.js` | Register new slices in store | TODO |

---

## Execution Order

1. **Phase 1**: A1.1, A1.2 (Root config fix)
2. **Phase 2**: A3.1-A3.3 (Analytics bug fix)
3. **Phase 3**: B1.1-B3.1 (Security fixes)
4. **Phase 4**: C1.1-C1.2 (N+1 query fix)
5. **Phase 5**: C2.1-C2.2 (Analytics models)
6. **Phase 6**: A2.1-A2.8 (Generate migrations)
7. **Phase 7**: C3.1 (Notification service)
8. **Phase 8**: C4.1 (Celery tasks)
9. **Phase 9**: C5.1 (Seed data)
10. **Phase 10**: D1.1-D1.6 (Frontend slices)
