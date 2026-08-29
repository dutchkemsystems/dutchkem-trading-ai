# Fix Architecture — Dutchkem Trading AI

## Date: 2026-08-28

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    ROOT LEVEL                            │
│  config/settings.py (thin wrapper)                      │
│  manage.py → config.settings (imports backend config)   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              BACKEND (dutchkem-trading-ai/backend/)      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   accounts   │  │   trading    │  │  indicators  │  │
│  │   models.py  │  │   models.py  │  │   models.py  │  │
│  │   admin.py   │  │   admin.py   │  │   admin.py   │  │
│  │   views.py   │  │   views.py   │  │   views.py   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   signals    │  │risk_management│  │   payments   │  │
│  │   models.py  │  │   models.py  │  │   models.py  │  │
│  │   admin.py   │  │   admin.py   │  │   admin.py   │  │
│  │   views.py   │  │   views.py   │  │   views.py   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │expert_advisors│ │mcp_integration│ │  market_data  │  │
│  │   models.py  │  │   models.py  │  │   models.py  │  │
│  │   admin.py   │  │   admin.py   │  │   admin.py   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │notifications │  │  analytics   │                     │
│  │   models.py  │  │  models.py   │ ← NEW               │
│  │   admin.py   │  │  admin.py    │ ← NEW               │
│  │  alerts.py   │  │  views.py    │                     │
│  └──────────────┘  └──────────────┘                     │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  strategies  │  │   config     │                     │
│  │ regime_switch│  │  celery.py   │                     │
│  │ strategy_map │  │  tasks.py    │                     │
│  └──────────────┘  │  celery_sched│                     │
│                    └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              FRONTEND (dutchkem-trading-ai/frontend/)    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │    store.js  │  │   App.js     │                     │
│  │  (Redux)     │  │  (Router)    │                     │
│  └──────────────┘  └──────────────┘                     │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │                  features/                        │   │
│  │  auth/ trading/ signals/ risk/ market/           │   │
│  │  payments/ eas/ analytics/ notifications/        │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │                   pages/                          │   │
│  │  Dashboard/ Trading/ Signals/ Risk/ Payments/    │   │
│  │  ExpertAdvisors/ Analytics/ Settings/ Login/     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Fix Implementation Order

### Phase 1: Critical Fixes (No Dependencies)
1. Fix root config conflict
2. Fix analytics field names
3. Fix security issues

### Phase 2: Database (After Phase 1)
4. Add analytics models
5. Generate all migrations

### Phase 3: Backend Quality (After Phase 2)
6. Add select_related for N+1
7. Complete notification service
8. Add Celery tasks
9. Create seed data command

### Phase 4: Frontend (After Phase 3)
10. Add missing Redux slices
11. Complete page implementations

---

## 3. Data Flow

```
User Request → Django View → Serializer → Model → Database
     │                                              │
     │              ┌───────────────────────────────┘
     │              ▼
     │         Celery Task
     │              │
     │              ▼
     │         Redis/RabbitMQ
     │              │
     │              ▼
     │         Worker Process
     │              │
     │              ▼
     │         Database Update
     │              │
     │              ▼
     │         WebSocket Channel Layer
     │              │
     │              ▼
     └──────→ Frontend (via WebSocket)
```

---

## 4. Security Architecture

```
┌─────────────────────────────────────────┐
│              SECURITY LAYERS             │
│                                          │
│  1. JWT Authentication                   │
│     └─ access_token (30min)             │
│     └─ refresh_token (7days)            │
│                                          │
│  2. Rate Limiting                        │
│     └─ anon: 100/hour                   │
│     └─ user: 1000/hour                  │
│     └─ FAIL_OPEN = False                │
│                                          │
│  3. CORS                                 │
│     └─ localhost:3000                    │
│     └─ credentials: true                │
│                                          │
│  4. Webhook Verification                 │
│     └─ HMAC-SHA256                       │
│     └─ Reject if no secret              │
│                                          │
│  5. Environment Variables                │
│     └─ All secrets in .env              │
│     └─ No hardcoded defaults            │
└─────────────────────────────────────────┘
```
