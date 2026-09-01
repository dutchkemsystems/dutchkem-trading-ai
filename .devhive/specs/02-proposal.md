# Proposal — Deployment Fixes

## Scope
Fix all critical deployment issues preventing production operation and provide comprehensive deployment documentation.

## Changes
1. Fix MT5 port defaults in settings_production.py
2. Add Celery worker + beat to render.yaml
3. Create docker-compose.full.yml (7 services)
4. Create populate_celery_schedule management command
5. Standardize MT5 Docker image references
6. Create DEPLOY.md (482 lines)
7. Update .env.example and env.production.example
8. Create PowerShell start/stop scripts

## Acceptance Criteria
- [x] MT5 connects correctly in local Docker and cloud
- [x] Celery worker processes all queues in production
- [x] Celery beat schedules periodic tasks via DatabaseScheduler
- [x] All services start/stop via scripts
- [x] Complete deployment documentation exists
