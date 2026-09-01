# =============================================================================
# Dutchkem Trading AI — Deployment Guide
# =============================================================================
# Complete guide for local development, local production, and cloud deployment.
# Covers MT5 terminal integration, service management, and start/stop procedures.
# =============================================================================

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Local Development Setup](#local-development-setup)
4. [Local Production (Docker Compose Full Stack)](#local-production-docker-compose-full-stack)
5. [Cloud Deployment (Render)](#cloud-deployment-render)
6. [MT5 Terminal Setup](#mt5-terminal-setup)
7. [Start / Pause / Stop Procedures](#start--pause--stop-procedures)
8. [Troubleshooting](#troubleshooting)
9. [Environment Variables Reference](#environment-variables-reference)

---

## Architecture Overview

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

### Services
| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache + Celery broker |
| MT5 Bridge REST | 8082 | MT5 API proxy |
| MT5 Bridge WebSocket | 8081 | MT5 real-time data |
| Django | 8000 | Web API + Admin |
| Celery Worker | — | Background tasks |
| Celery Beat | — | Periodic task scheduler |

---

## Prerequisites

### For Local Development
- Python 3.10+
- Git
- MetaTrader 5 terminal (Windows only)

### For Local Production (Docker)
- Docker Desktop 4.x+
- Docker Compose v2+
- MetaTrader 5 terminal (Windows only)
- 8GB+ RAM recommended

### For Cloud Deployment (Render)
- GitHub account
- Render account (free tier available)
- Cloudflare account (for MT5 tunnel)

---

## Local Development Setup

### Step 1: Clone and configure
```bash
git clone https://github.com/your-org/dutchkem-trading-ai.git
cd dutchkem-trading-ai
copy .env.example .env
```

### Step 2: Edit .env
```ini
USE_SQLITE=1
MT5_HOST=localhost
MT5_PORT=8082
MT5_WS_PORT=8081
```

### Step 3: Install dependencies
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Step 4: Run migrations
```bash
python manage.py migrate
python manage.py createsuperuser
```

### Step 5: Start MT5 Bridge (separate terminal)
```powershell
.\scripts\start-mt5.ps1
```

### Step 6: Start Django
```bash
python manage.py runserver
```

### Quick Start (all-in-one)
```powershell
.\scripts\quick-start.ps1
```

---

## Local Production (Docker Compose Full Stack)

This runs ALL services in Docker, identical to production.

### Start all services
```powershell
.\scripts\start-local.ps1
```

### Start without MT5 bridge
```powershell
.\scripts\start-local.ps1 -SkipMT5
```

### Manual start
```bash
docker compose -f docker-compose.full.yml up -d
```

### Stop all services
```powershell
.\scripts\stop-local.ps1
```

### Stop and remove data (DESTRUCTIVE)
```powershell
.\scripts\stop-local.ps1 -Volumes
```

### View logs
```bash
# All services
docker compose -f docker-compose.full.yml logs -f

# Specific service
docker compose -f docker-compose.full.yml logs -f django
docker compose -f docker-compose.full.yml logs -f celery-worker
docker compose -f docker-compose.full.yml logs -f mt5-bridge
```

### Populate Celery Beat schedule (first time only)
```bash
docker compose -f docker-compose.full.yml exec django python manage.py populate_celery_schedule
```

---

## Cloud Deployment (Render)

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Production deployment"
git push origin main
```

### Step 2: Create Render account and import Blueprint
1. Go to https://dashboard.render.com
2. Click "New" → "Blueprint"
3. Select your GitHub repo
4. Render will detect `render.yaml` and create:
   - **Web service** (Django)
   - **Worker** (Celery Worker)
   - **Worker** (Celery Beat)
   - **PostgreSQL** database

### Step 3: Configure environment variables
In Render Dashboard → Environment, set:

| Variable | Value | Notes |
|----------|-------|-------|
| `SECRET_KEY` | (auto-generated) | Do not change |
| `DATABASE_URL` | (auto-linked) | From PostgreSQL |
| `REDIS_URL` | (manual) | Create Redis in Render |
| `CELERY_BROKER_URL` | (manual) | Same as REDIS_URL with /1 |
| `MT5_HOST` | `mt5.yourdomain.com` | Cloudflare tunnel URL |
| `MT5_PORT` | `443` | Tunnel port |
| `MT5_WS_PORT` | `443` | Tunnel port |
| `MT5_LOGIN` | (your MT5 login) | |
| `MT5_PASSWORD` | (your MT5 password) | |
| `MT5_SERVER` | (your broker server) | |

### Step 4: Create Redis in Render
1. Render Dashboard → New → Redis
2. Plan: Free (25MB)
3. Copy Internal URL to `REDIS_URL` and `CELERY_BROKER_URL`

### Step 5: Set up Cloudflare Tunnel for MT5
```bash
# Install cloudflared
# Create tunnel
cloudflared tunnel create dutchkem-mt5
cloudflared tunnel route dns dutchkem-mt5 mt5.yourdomain.com

# Run tunnel (on your Windows machine with MT5)
cloudflared tunnel run dutchkem-mt5
```

### Step 6: Populate Celery schedule
In Render Shell (or first deploy):
```bash
python manage.py populate_celery_schedule
```

### Step 7: Verify deployment
```bash
# Check health
curl https://dutchkem-trading-ai.onrender.com/health/

# Check admin
open https://dutchkem-trading-ai.onrender.com/admin/
```

---

## MT5 Terminal Setup

### Windows MetaTrader 5 Configuration

1. **Open MetaTrader 5** terminal
2. Go to **Tools** → **Options**
3. Under **Expert Advisors**:
   - ✅ Allow algorithmic trading
   - ✅ Allow WebRequest for listed URL
   - Add: `http://localhost:8082`
4. Under **Server**:
   - Note the **port** (default: 1929)
   - This is set in `MT5_MT5_PORT` env var

### Connection Flow
```
MT5 Terminal (1929) ←→ MT5 Bridge (8082/8081) ←→ Django Backend
```

### Verifying MT5 Connection
```bash
# Check bridge health
curl http://localhost:8082/health

# Connect to MT5
curl -X POST http://localhost:8082/connect \
  -H "Content-Type: application/json" \
  -d '{}'

# Get account info
curl -X POST http://localhost:8082/tools/get_account_info \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_account_info", "params": {}}'
```

---

## Start / Pause / Stop Procedures

### LOCAL DEVELOPMENT

#### Start
```powershell
# Start MT5 bridge
.\scripts\start-mt5.ps1

# Start Django dev server
cd backend
python manage.py runserver
```

#### Pause (pause trading without stopping services)
```bash
# Via Django admin
# 1. Go to http://localhost:8000/admin/django_celery_beat/periodictask/
# 2. Find "run-v6-trading-cycle" task
# 3. Uncheck "Enabled" → Save
```

#### Stop
```powershell
# Stop MT5 bridge
.\scripts\stop-mt5.ps1

# Stop Django (Ctrl+C in terminal)
```

### LOCAL PRODUCTION (Docker)

#### Start
```powershell
.\scripts\start-local.ps1
```

#### Pause (pause trading)
```bash
# Pause Celery Beat (stops all periodic tasks)
docker compose -f docker-compose.full.yml stop celery-beat

# Or pause only trading cycle
docker compose -f docker-compose.full.yml exec celery-worker \
  celery -A config.celery control cancel run-v6-trading-cycle
```

#### Stop
```powershell
.\scripts\stop-local.ps1
```

#### Stop MT5 bridge only
```powershell
.\scripts\stop-mt5.ps1
```

### CLOUD (Render)

#### Start
- Auto-deploys on git push to main branch
- Manual: Render Dashboard → Manual Deploy → Deploy latest commit

#### Pause (pause trading)
1. Render Dashboard → dutchkem-celery-beat → Suspend
   - This stops all periodic task scheduling
2. Or: Django Admin → Periodic Tasks → Disable specific tasks

#### Stop
1. Render Dashboard → dutchkem-trading-ai → Suspend
2. Render Dashboard → dutchkem-celery-worker → Suspend
3. Render Dashboard → dutchkem-celery-beat → Suspend

#### Full Stop (all services)
Render Dashboard → each service → Suspend

---

## Troubleshooting

### MT5 Bridge won't connect
1. Check MT5 terminal is running
2. Verify "Allow WebRequest" is enabled in MT5
3. Check MT5 API port (default: 1929)
4. Verify bridge container is healthy:
   ```bash
   docker logs dutchkem-mt5-bridge
   curl http://localhost:8082/health
   ```

### Celery Worker not processing tasks
1. Check Redis is running:
   ```bash
   docker compose -f docker-compose.full.yml exec redis redis-cli ping
   ```
2. Check worker logs:
   ```bash
   docker compose -f docker-compose.full.yml logs celery-worker
   ```
3. Verify Celery Beat schedule is populated:
   ```bash
   docker compose -f docker-compose.full.yml exec django \
     python manage.py populate_celery_schedule --dry-run
   ```

### Database connection refused
1. Check PostgreSQL is running:
   ```bash
   docker compose -f docker-compose.full.yml exec db pg_isready
   ```
2. Verify DATABASE_URL matches:
   ```
   postgresql://dutchkem:dutchkem_trading@db:5432/dutchkem_trading
   ```

### Port conflicts
```bash
# Check what's using the port
netstat -ano | findstr :8000
netstat -ano | findstr :8082
netstat -ano | findstr :5432

# Kill process if needed
taskkill /PID <PID> /F
```

### Render deployment fails
1. Check build logs in Render Dashboard
2. Verify all environment variables are set
3. Ensure Redis is created and linked
4. Check `render.yaml` syntax

---

## Environment Variables Reference

### Required (must set)
| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `y0i%ub%h*r8fz!c!...` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | Celery broker | `redis://localhost:6379/1` |
| `MT5_HOST` | MT5 bridge host | `localhost` or `mt5.domain.com` |
| `MT5_PORT` | MT5 REST port | `8082` (local) or `443` (cloud) |
| `MT5_WS_PORT` | MT5 WebSocket port | `8081` (local) or `443` (cloud) |
| `MT5_LOGIN` | MT5 account number | `12345678` |
| `MT5_PASSWORD` | MT5 account password | `your-password` |
| `MT5_SERVER` | MT5 broker server | `BrokerDemo` |

### Optional
| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `0` |
| `USE_SQLITE` | Use SQLite instead of PostgreSQL | `0` |
| `MT5_TIMEOUT` | MT5 request timeout (seconds) | `10` |
| `MT5_MAX_RETRIES` | MT5 connection retry count | `5` |
| `MT5_RETRY_DELAY` | Delay between retries (seconds) | `2.0` |
| `MT5_MT5_PORT` | MT5 terminal API port | `1929` |
| `CLOUDINARY_URL` | Cloudinary media storage | — |
| `KORA_SECRET_KEY` | Korapay payment key | — |
| `ALLOWED_HOSTS` | Django allowed hosts | `localhost` |
| `CORS_ALLOWED_ORIGINS` | CORS origins | `http://localhost:3000` |
| `SECURE_SSL_REDIRECT` | Force HTTPS | `False` |

---

## File Structure

```
dutchkem-trading-ai/
├── backend/
│   ├── config/
│   │   ├── settings_production.py    # Production Django settings
│   │   ├── celery.py                 # Celery app configuration
│   │   ├── celery_schedule.py        # Beat schedule definitions
│   │   ├── tasks.py                  # All Celery tasks
│   │   └── management/
│   │       └── commands/
│   │           └── populate_celery_schedule.py  # Load beat schedule
│   ├── mcp_integration/
│   │   └── services.py              # MT5 service layer
│   ├── infrastructure/
│   │   └── mt5_pool.py              # MT5 connection pooling
│   └── requirements.txt
├── mt5-bridge/
│   ├── docker-compose.yml           # Standalone MT5 bridge
│   └── .env                         # MT5 bridge credentials
├── scripts/
│   ├── start-local.ps1              # Start all local services
│   ├── stop-local.ps1               # Stop all local services
│   ├── start-mt5.ps1                # Start MT5 bridge
│   ├── stop-mt5.ps1                 # Stop MT5 bridge
│   └── quick-start.ps1              # Quick dev setup
├── docker-compose.yml               # Basic services (db, redis, django, celery)
├── docker-compose.full.yml          # Full stack (includes MT5 bridge)
├── Dockerfile                       # Python 3.12 + gunicorn
├── render.yaml                      # Render Blueprint (3 services)
├── .env.example                     # Dev environment template
├── env.production.example           # Production environment template
└── DEPLOY.md                        # This file
```
