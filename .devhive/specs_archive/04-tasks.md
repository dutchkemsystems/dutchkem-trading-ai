# Task Plan — Deployment Fixes

## Infrastructure Tasks
- [x] Fix MT5 port inconsistency in settings_production.py (8082/8081 defaults)
- [x] Update render.yaml with Celery worker and beat services
- [x] Create docker-compose.yml with MT5 bridge included
- [x] Fix duplicate MT5 image reference (standardize on ghcr.io/synx-ai/synx-mt5-mcp:latest)

## Backend Tasks
- [x] Create populate_celery_schedule management command

## Documentation Tasks
- [x] Create comprehensive DEPLOY.md
- [x] Update .env.example with correct MT5 ports and credentials
- [x] Update env.production.example with clear documentation

## Frontend Tasks
- [ ] None required

## Performance Tasks
- [ ] None required

## Release Tasks
- [ ] None required
