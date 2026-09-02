# Architecture — Deployment

## Service Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                        HOST MACHINE                              │
│                                                                  │
│  ┌──────────────┐     ┌──────────────────────────────────────┐  │
│  │ MetaTrader 5  │────▶│  MT5 Bridge (Docker)                  │  │
│  │ (Port 1929)   │     │  REST: 8082  │  WebSocket: 8081      │  │
│  └──────────────┘     └──────────┬───────────────────────────┘  │
│                                   │                              │
│  ┌───────────────────────────────┼──────────────────────────┐   │
│  │          Docker Compose        │                          │   │
│  │                                ▼                          │   │
│  │  ┌──────────┐  ┌───────┐  ┌──────────┐  ┌────────────┐  │   │
│  │  │ PostgreSQL│  │ Redis │  │  Django   │  │Celery Worker│  │   │
│  │  │  (5432)   │  │(6379) │  │  (8000)  │  │            │  │   │
│  │  └──────────┘  └───────┘  └──────────┘  └────────────┘  │   │
│  │                                                           │   │
│  │  ┌────────────────┐                                       │   │
│  │  │  Celery Beat    │                                      │   │
│  │  │  (Scheduler)    │                                      │   │
│  │  └────────────────┘                                       │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Files Modified
| File | Change |
|------|--------|
| `backend/config/settings_production.py` | MT5_PORT default 3000→8082, MT5_WS_PORT default 3001→8081 |
| `render.yaml` | Added worker (celery-worker) and worker (celery-beat) services |
| `docker-compose.yml` | Created with all 7 services including MT5 bridge |
| `backend/config/management/commands/populate_celery_schedule.py` | Created management command |
| `mt5-bridge/docker-compose.yml` | Standardized image to ghcr.io/synx-ai/synx-mt5-mcp:latest |
| `.env.example` | Updated MT5 ports to 8082/8081, added MT5 credentials |
| `env.production.example` | Enhanced with clear documentation |
| `DEPLOY.md` | Created comprehensive deployment guide |
| `scripts/start-local.ps1` | Created full stack startup script |
| `scripts/stop-local.ps1` | Created full stack shutdown script |
| `scripts/start-mt5.ps1` | Created MT5 bridge startup script |
| `scripts/stop-mt5.ps1` | Created MT5 bridge shutdown script |
