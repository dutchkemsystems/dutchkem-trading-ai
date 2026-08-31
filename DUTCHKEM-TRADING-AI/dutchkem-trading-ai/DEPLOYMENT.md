# Dutchkem Trading AI 2.0 — Free Tier Deployment Guide

## Overview

This guide covers deploying Dutchkem Trading AI 2.0 using free-tier services.
The stack uses Django, PostgreSQL, Redis, Celery, and a React frontend.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│  PostgreSQL  │
│  (Vercel)    │     │  (Railway)   │     │  (Railway)   │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────┴───────┐
                    │    Redis     │
                    │  (Railway)   │
                    └──────────────┘
```

---

## Free Tier Options

### Option 1: Railway (Recommended)
- **Backend**: $5 free credit/month
- **PostgreSQL**: Included in Railway
- **Redis**: Included in Railway
- **Celery Worker**: Runs on same Railway instance

### Option 2: Render
- **Backend**: Free tier (spins down after inactivity)
- **PostgreSQL**: Free 90-day trial
- **Redis**: Upstash free tier (10k commands/day)

### Option 3: Fly.io
- **Backend**: 3 shared-cpu-1x VMs free
- **PostgreSQL**: Fly Postgres free (3GB)
- **Redis**: Upstash free tier

---

## Step-by-Step: Railway Deployment

### 1. Prerequisites
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login
```

### 2. Create Project
```bash
cd dutchkem-trading-ai/backend
railway init
```

### 3. Add Services
```bash
# PostgreSQL
railway add --database postgresql

# Redis
railway add --plugin redis
```

### 4. Configure Environment Variables
```bash
railway variables set SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
railway variables set DEBUG=False
railway variables set ALLOWED_HOSTS="*.railway.app"
railway variables set DJANGO_SETTINGS_MODULE=config.settings_production
```

### 5. Deploy
```bash
railway up
```

### 6. Run Migrations
```bash
railway run python manage.py migrate
railway run python manage.py createsuperuser
```

---

## Step-by-Step: Render Deployment

### 1. Connect GitHub Repo
- Go to [render.com](https://render.com)
- Create new **Web Service** from GitHub
- Select the `backend` directory

### 2. Build Settings
```
Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput
Start Command: gunicorn config.wsgi:application
```

### 3. Environment Variables
```
SECRET_KEY=<generate-one>
DEBUG=False
DATABASE_URL=<from Render PostgreSQL>
REDIS_URL=<from Upstash>
DJANGO_SETTINGS_MODULE=config.settings_production
```

### 4. Add PostgreSQL
- Create new **PostgreSQL** instance on Render
- Copy the Internal Database URL to `DATABASE_URL`

### 5. Add Redis (Upstash)
- Sign up at [upstash.com](https://upstash.com) (free tier)
- Create Redis database
- Copy the URL to `REDIS_URL`

---

## Step-by-Step: Fly.io Deployment

### 1. Install Fly CLI
```bash
curl -L https://fly.io/install.sh | sh
fly auth signup
```

### 2. Initialize
```bash
cd backend
fly launch
```

### 3. Set Secrets
```bash
fly secrets set SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
fly secrets set DEBUG=False
fly secrets set DATABASE_URL=<your-postgres-url>
fly secrets set REDIS_URL=<your-redis-url>
```

### 4. Deploy
```bash
fly deploy
```

---

## MT5 Bridge Deployment

The MetaTrader 5 integration requires a separate bridge server.

### Option A: Oracle Cloud Free Tier
- Always-free AMD instance (1 OCPU, 1GB RAM)
- Install MT5 on Windows VM via RDP
- Expose MCP bridge on internal network

### Option B: Local + Cloudflare Tunnel
- Run MT5 locally
- Use Cloudflare Tunnel to expose the MCP bridge
```bash
cloudflared tunnel --url http://localhost:3000
```

### Option C: AWS Free Tier
- t2.micro instance (750 hours/month for 12 months)
- Install MT5 + MCP bridge

---

## Celery Worker Deployment

### On Railway
Add a **Worker** service:
```toml
# railway.toml
[services.worker]
startCommand = "celery -A config worker -l info -c 2"
```

### On Render
Create a second **Background Worker**:
```
Start Command: celery -A config worker -l info -c 2
```

### On Fly.io
Add to `fly.toml`:
```toml
[processes]
web = "gunicorn config.wsgi:application"
worker = "celery -A config worker -l info -c 2"
```

---

## Frontend Deployment (Vercel)

```bash
cd frontend
npm install
npm run build
vercel deploy --prod
```

Environment variables for frontend:
```
REACT_APP_API_URL=https://your-backend.railway.app/api/v1
REACT_APP_WS_URL=wss://your-backend.railway.app/ws
```

---

## Domain & SSL

All recommended platforms provide:
- Free SSL certificates (Let's Encrypt)
- Custom domain support
- Automatic HTTPS

### Custom Domain Setup
1. Add domain in platform dashboard
2. Update DNS records:
   ```
   CNAME  www     -> your-app.railway.app
   A      @       -> your-app.railway.app
   ```
3. Wait for SSL provisioning (automatic)

---

## Monitoring & Alerts

### Free Monitoring Options
- **UptimeRobot**: Free 50 monitors
- **Betterstack**: Free 5 monitors
- **Sentry**: Free 5k errors/month

### Setup Sentry
```bash
pip install sentry-sdk
```

```python
# config/settings.py
import sentry_sdk
sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=0.1,
)
```

---

## Cost Summary (Free Tier)

| Service | Provider | Cost |
|---------|----------|------|
| Backend | Railway | $5 credit/month |
| PostgreSQL | Railway | Included |
| Redis | Railway | Included |
| Frontend | Vercel | Free (100GB bandwidth) |
| MT5 Bridge | Oracle Cloud | Always free |
| Monitoring | Sentry | Free (5k errors) |
| **Total** | | **~$0/month** |

---

## Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Generate secure `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up `EMAIL_BACKEND` for notifications
- [ ] Configure CORS origins
- [ ] Set up Sentry for error tracking
- [ ] Enable rate limiting
- [ ] Configure static file serving
- [ ] Set up database backups
- [ ] Configure Celery beat schedule
- [ ] Set up MT5 bridge connectivity
- [ ] Test all API endpoints
- [ ] Verify WebSocket connections
- [ ] Load test with k6 or artillery

---

## Troubleshooting

### Common Issues

**Static files not loading**
```bash
python manage.py collectstatic --noinput
```

**Database connection errors**
- Check `DATABASE_URL` is set correctly
- Ensure PostgreSQL is running and accessible

**Celery not processing tasks**
- Verify Redis is accessible
- Check `CELERY_BROKER_URL` matches Redis URL
- Ensure worker is running: `celery -A config worker -l info`

**MT5 connection refused**
- Verify MT5 bridge is running
- Check `MT5_HOST` and `MT5_PORT` environment variables
- Ensure firewall allows the connection

---

## Recent Changes (v2.1)

### Bug Fixes Applied
1. **Position Size Calculation** — Fixed formula to include `pip_value = contract_size * pip_size`
2. **Async Event Loops** — Replaced `asyncio.new_event_loop()` with `asyncio.run()` + ThreadPoolExecutor fallback
3. **MACD Signal Line** — Now computes actual EMA of MACD line instead of copying MACD
4. **Stochastic %D** — Now computes SMA of %K over d_period
5. **Ensemble S/R & Volatility** — Models are always called (using current_features as fallback)
6. **Celery Schedule** — Multi-symbol support: EURUSD, GBPUSD, USDJPY, AUDUSD, XAUUSD
7. **Signal History** — No longer references non-existent user FK

### New Features
- **Portfolio-Level Risk** — Correlation checks, exposure limits, directional balance
- **Equity Curve Trading** — Position sizing reduced 50% when equity below 20-period MA
- **Kelly Criterion** — Fractional Kelly position sizing (35% of full Kelly)
- **Drawdown Recovery Tiers** — 5-10%: reduce 50%, 10-15%: Gold Edge only, 15-20%: halt, 20%+: full stop
- **Session-Based Filter** — Boost during London/NY overlap, reduce during Asian session
- **Feature Store** — Redis-backed ML feature cache with in-memory fallback
- **Auto-Retraining** — Accuracy tracking, KL divergence drift detection, weekly scheduled retrain
- **Audit Log** — Full audit trail for trades, signals, risk events, user actions

### Deployment Notes
- Run `python manage.py makemigrations audit` after pull
- Run `python manage.py migrate` to apply audit log table
- Multi-symbol Celery schedule is generated dynamically from `ACTIVE_SYMBOLS` list in `celery_schedule.py`
- Redis is optional in dev — Feature Store and Auto-Retrain use in-memory fallback when Redis is unavailable
