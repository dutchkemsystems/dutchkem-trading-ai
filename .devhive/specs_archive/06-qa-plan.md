# QA Plan — Deployment Fixes

## Test Scenarios

### 1. MT5 Port Configuration
- [x] Verify settings_production.py defaults to 8082/8081
- [x] Verify .env.example shows correct ports
- [x] Verify env.production.example documents port mapping

### 2. Render Deployment
- [x] Verify render.yaml defines 3 services (web, worker, worker)
- [x] Verify all services share DATABASE_URL and REDIS_URL
- [x] Verify Celery worker command includes all queues
- [x] Verify Celery beat uses DatabaseScheduler

### 3. Docker Compose Full Stack
- [x] Verify docker-compose.full.yml includes all 7 services
- [x] Verify MT5 bridge uses ghcr.io/synx-ai/synx-mt5-mcp:latest
- [x] Verify port mappings are correct (8082:8082, 8081:8081)
- [x] Verify health checks are configured

### 4. Management Command
- [x] Verify populate_celery_schedule.py exists
- [x] Verify it supports --clear and --dry-run flags
- [x] Verify it handles both interval and crontab schedules

### 5. Scripts
- [x] Verify start-local.ps1 starts all services
- [x] Verify stop-local.ps1 stops all services
- [x] Verify start-mt5.ps1 starts MT5 bridge
- [x] Verify stop-mt5.ps1 stops MT5 bridge
