# Exploration Report — Deployment Fixes

## Findings

### Critical Issues Found
1. **MT5 Port Inconsistency**: settings_production.py defaulted to 3000/3001 (internal container ports) but Docker maps to 8082/8081. **FIXED**: Changed defaults to 8082/8081.

2. **Missing Celery Services on Render**: render.yaml only defined web service. Trading cycle, signal generation, and market data ingestion wouldn't run. **FIXED**: Added worker and beat services.

3. **MT5 Bridge Isolation**: Users had to start MT5 bridge separately with no documentation. **FIXED**: Created docker-compose.full.yml with all services integrated.

4. **Celery Beat Schedule Empty**: DatabaseScheduler was configured but schedule never populated. **FIXED**: Created populate_celery_schedule management command.

### Minor Issues Fixed
- Duplicate MT5 image references standardized to ghcr.io/synx-ai/synx-mt5-mcp:latest
- .env.example updated with correct ports and MT5 credentials
- env.production.example enhanced with clear documentation
