# Product Requirements Document — Dutchkem Trading AI Fix-All Pipeline

## Project: Dutchkem Trading AI
## Date: 2026-08-28
## Status: In Progress

---

## 1. Executive Summary

Dutchkem Trading AI is a Django 6.1 + React 18 forex trading platform (~65% complete). This PRD documents all identified issues that must be fixed to reach production readiness.

---

## 2. Critical Blockers (P0)

### 2.1 Root Config Conflict
- **Issue**: Root `config/settings.py` is a bare Django 6.1 default (SQLite, no apps) conflicting with `backend/config/settings.py` (the real production config)
- **Impact**: Root manage.py points to wrong settings, causing Django to use incomplete config
- **Fix**: Remove root config conflict or make root manage.py point to correct settings

### 2.2 Missing Migrations
- **Issue**: Only `trading` and `signals` have migration files. All other apps (accounts, indicators, risk_management, payments, expert_advisors, mcp_integration, market_data, notifications) need migrations
- **Impact**: Cannot run `migrate`, database schema incomplete
- **Fix**: Generate migrations for all apps

### 2.3 Analytics Field Name Bugs
- **Issue**: `analytics/views.py` references `close_time` and `pnl` but Trade model has `closed_at` and `profit_loss`
- **Impact**: Analytics views crash at runtime with AttributeError
- **Fix**: Replace field references with correct model field names

---

## 3. Security Issues (P0)

### 3.1 Hardcoded Secrets
- **Issue**: DB password "dutchkem_secure_2024" in settings, secret key "django-insecure-change-this-in-production"
- **Fix**: Use environment variables for all secrets, set secure defaults

### 3.2 Rate Limiting Fail-Open
- **Issue**: `RATELIMIT_FAIL_OPEN = True` allows requests through when rate limiter fails
- **Fix**: Set to `False` for production

### 3.3 Korapay Webhook Signature Bypass
- **Issue**: Webhook returns True if secret not set (line 110 of korapay.py)
- **Fix**: Reject webhooks when secret is not configured

---

## 4. Backend Issues (P1)

### 4.1 Analytics Bug
- **Issue**: Views reference `close_time` and `pnl` but model has `closed_at` and `profit_loss`
- **Fix**: Update field references in analytics/views.py

### 4.2 N+1 Queries
- **Issue**: `TradeListView` doesn't select_related foreign keys
- **Fix**: Add select_related for symbol, timeframe, signal, expert_advisor

### 4.3 Async/Sync Mixing
- **Issue**: `OrderExecutionService` creates `asyncio.new_event_loop()` in sync Django views
- **Fix**: Use synchronous wrappers or asyncio.run()

### 4.4 Missing Celery Periodic Tasks
- **Issue**: Daily risk reset, signal generation, data ingestion not scheduled via Celery Beat
- **Fix**: Configure celery_schedule.py with proper periodic tasks

### 4.5 Missing Seed Data
- **Issue**: No management commands for initial symbols, timeframes, indicators
- **Fix**: Create seed_data management command

### 4.6 Notifications Incomplete
- **Issue**: No email/SMS/push sending code
- **Fix**: Complete notification service with email, SMS, and push support

---

## 5. Infrastructure Issues (P2)

### 5.1 WebSocket Routing
- **Issue**: `config/websocket_routing.py` needs verification
- **Status**: Routing exists, needs review

### 5.2 InfluxDB Pipeline
- **Issue**: Configured but ingestion pipeline needs verification
- **Status**: Configuration exists, needs testing

---

## 6. Acceptance Criteria

- [ ] All migrations generated and applied
- [ ] Analytics views use correct field names
- [ ] No hardcoded secrets in codebase
- [ ] Rate limiting fails closed
- [ ] Webhook signature verification enforced
- [ ] N+1 queries resolved with select_related
- [ ] Celery periodic tasks configured
- [ ] Seed data management command exists
- [ ] Notification service complete
