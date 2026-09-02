# DutchKEM Trading AI — Complete Usage Guide

> **Generated:** September 1, 2026  
> **MT5 Account:** <YOUR_MT5_ACCOUNT> | **Server:** <YOUR_MT5_SERVER>  
> **Trading Mode:** FULL (Automatic)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Prerequisites](#2-prerequisites)
3. [Docker Desktop Installation](#3-docker-desktop-installation)
4. [Local Production Setup](#4-local-production-setup)
5. [Render Cloud Deployment](#5-render-cloud-deployment)
6. [Trading Operations](#6-trading-operations)
7. [Monitoring & Dashboard](#7-monitoring--dashboard)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. System Overview

DutchKEM Trading AI is an automated forex/gold trading system with:

- **MT5 Bridge:** Connects to MetaTrader 5 via SYNX-MT5-MCP
- **Django Backend:** REST API, user management, trade execution
- **Celery Workers:** Background tasks for trading cycles, signals, risk monitoring
- **Celery Beat:** Scheduled tasks (trading cycle every 60 seconds)
- **PostgreSQL:** Production database
- **Redis:** Task queue and caching

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DUTCHKEM TRADING AI                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │ Frontend │───▶│  Django  │───▶│ Celery   │               │
│  │ (React)  │    │ Backend  │    │ Worker   │               │
│  └──────────┘    └──────────┘    └──────────┘               │
│                       │                  │                   │
│                       ▼                  ▼                   │
│                ┌──────────┐      ┌──────────┐               │
│                │PostgreSQL│      │  Redis   │               │
│                └──────────┘      └──────────┘               │
│                       │                  │                   │
│                       ▼                  ▼                   │
│                ┌─────────────────────────────┐               │
│                │      MT5 Bridge (Docker)    │               │
│                └─────────────────────────────┘               │
│                              │                              │
│                              ▼                              │
│                ┌─────────────────────────────┐               │
│                │   MetaTrader 5 Terminal     │               │
│                │   (<YOUR_MT5_SERVER>)      │               │
│                └─────────────────────────────┘               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Active Trading Symbols

- EURUSD (Euro/US Dollar)
- GBPUSD (British Pound/US Dollar)
- USDJPY (US Dollar/Japanese Yen)
- AUDUSD (Australian Dollar/US Dollar)
- XAUUSD (Gold/US Dollar)

### Automated Trading Pipeline (V6.5)

Every 60 seconds, the system runs:

```
Scan Market → AI Analysis → Sentiment → News → Order Flow → Pattern Recognition →
Multi-Timeframe Analysis → Signal Generation → Risk Management →
Stop Loss/Take Profit → Diversification → Trade Execution → Learning
```

---

## 2. Prerequisites

- [x] Windows 10/11 with WSL2 support
- [x] Docker Desktop (to be installed — see Section 3)
- [x] MetaTrader 5 terminal installed and logged in
- [x] Render account (for cloud deployment)
- [x] Git installed
- [x] Python 3.12+ (for local dev without Docker)

---

## 3. Docker Desktop Installation

Since Docker is not installed on your system, follow these steps:

### Step 3.1: Download Docker Desktop

1. Go to: https://www.docker.com/products/docker-desktop/
2. Click **"Download for Windows"**
3. Save `Docker Desktop Installer.exe`

### Step 3.2: Install Docker Desktop

1. Run the downloaded installer
2. Ensure **"Use WSL 2 instead of Hyper-V"** is checked
3. Click **OK** and wait for installation
4. When prompted, **restart your computer**

### Step 3.3: Post-Installation Setup

After restart:

1. Launch Docker Desktop from Start Menu
2. Wait for Docker Engine to start (green icon in system tray)
3. Open PowerShell and verify:
   ```powershell
   docker --version
   docker compose version
   ```

### Step 3.4: Enable WSL2 (if not already enabled)

Open PowerShell as Administrator:
```powershell
wsl --install
wsl --set-default-version 2
```

Restart if prompted.

### Step 3.5: Allocate Resources

In Docker Desktop:
1. Go to **Settings** (gear icon)
2. **Resources** → **Advanced**
3. Set:
   - CPUs: 4 (or half your cores)
   - Memory: 8 GB (or half your RAM)
   - Swap: 2 GB
4. Click **Apply & Restart**

---

## 4. Local Production Setup

### Step 4.1: Start MT5 Terminal

1. Open MetaTrader 5
2. Login with:
   - **Login:** <YOUR_MT5_LOGIN>
   - **Password:** <YOUR_MT5_PASSWORD>
   - **Server:** <YOUR_MT5_SERVER>
3. Ensure **"Allow Algo Trading"** is enabled (Tools → Options → Expert Advisors)
4. Keep MT5 running in the background

### Step 4.2: Start All Services

Open PowerShell in the project directory and run:

```powershell
# Start PostgreSQL, Redis, MT5 Bridge, Django, Celery Worker, Celery Beat
docker compose -f docker-compose.yml up -d
```

This will:
- Start PostgreSQL on port 5432
- Start Redis on port 6379
- Start MT5 Bridge on ports 8082 (REST) and 8081 (WebSocket)
- Start Django on port 8000
- Start Celery Worker
- Start Celery Beat (scheduler)

### Step 4.3: Verify Services

```powershell
# Check all containers are running
docker compose -f docker-compose.yml ps

# Check Django health
curl http://localhost:8000/health/

# Check MT5 Bridge health
curl http://localhost:8082/health
```

### Step 4.4: Create Admin User

```powershell
# Access Django shell inside the container
docker compose -f docker-compose.yml exec django python manage.py createsuperuser

# Enter username, email, and password when prompted
```

### Step 4.5: Run Database Migrations

```powershell
docker compose -f docker-compose.yml exec django python manage.py migrate --no-input
```

### Step 4.6: Access the System

| Service | URL |
|---------|-----|
| Django Backend | http://localhost:8000 |
| Admin Panel | http://localhost:8000/admin/ |
| API Docs | http://localhost:8000/api/docs/ |
| MT5 Bridge REST | http://localhost:8082 |
| MT5 Bridge WebSocket | ws://localhost:8081 |

### Step 4.7: View Logs

```powershell
# All services
docker compose -f docker-compose.yml logs -f

# Specific service
docker compose -f docker-compose.yml logs -f django
docker compose -f docker-compose.yml logs -f celery-worker
docker compose -f docker-compose.yml logs -f mt5-bridge
```

---

## 5. Render Cloud Deployment

### Step 5.1: Push to GitHub

```powershell
git add .
git commit -m "feat: production deployment with MT5 credentials"
git push origin main
```

### Step 5.2: Deploy via Render Blueprint

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository: `dutchkemsystems/dutchkem-trading-ai`
4. Render will detect `render.yaml` and create:
   - Web service (Django)
   - Celery Worker
   - Celery Beat
   - PostgreSQL database
5. Click **"Apply"**

### Step 5.3: Set Manual Environment Variables

In Render Dashboard, for each service, set these variables manually:

| Variable | Value | Notes |
|----------|-------|-------|
| `REDIS_URL` | (from Render Redis) | Create Redis in Dashboard first |
| `CELERY_BROKER_URL` | (same as REDIS_URL) | Same Redis, different DB index |
| `MT5_HOST` | (your bridge URL) | See Section 5.5 |
| `CLOUDINARY_URL` | (if using) | Optional media storage |

### Step 5.4: Create Redis in Render

1. In Render Dashboard: **"New +"** → **"Redis"**
2. Name: `dutchkem-redis`
3. Plan: Free
4. Copy the **Internal URL**
5. Set as `REDIS_URL` and `CELERY_BROKER_URL` in all 3 services

### Step 5.5: MT5 Bridge for Cloud (Important!)

For cloud deployment, you need a way to expose your local MT5 terminal to Render. Options:

#### Option A: Cloudflare Tunnel (Recommended)

```powershell
# Install cloudflared
winget install Cloudflare.cloudflared

# Login
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create dutchkem-mt5

# Configure (add to ~/.cloudflared/config.yml)
tunnel: <tunnel-id>
credentials-file: C:\Users\<you>\.cloudflared\<tunnel-id>.json
ingress:
  - hostname: mt5.dutchkem.com
    service: http://localhost:8082
  - service: http_status:404

# Route DNS
cloudflared tunnel route dns dutchkem-mt5 mt5.dutchkem.com

# Run tunnel
cloudflared tunnel run dutchkem-mt5
```

Then set in Render:
- `MT5_HOST=mt5.dutchkem.com`
- `MT5_PORT=443`
- `MT5_WS_PORT=443`

#### Option B: Leave MT5 Host Empty (Partial Functionality)

If you don't set up a tunnel, the system will run but won't be able to execute real trades. It will still generate signals and calculate indicators.

### Step 5.6: Run Migrations on Render

After deployment:
1. Go to your web service → **"Shell"** tab
2. Run:
```bash
python manage.py migrate --no-input
python manage.py createsuperuser
```

### Step 5.7: Verify Deployment

| Service | URL |
|---------|-----|
| Backend API | https://dutchkem-trading-ai.onrender.com |
| Admin Panel | https://dutchkem-trading-ai.onrender.com/admin/ |
| API Docs | https://dutchkem-trading-ai.onrender.com/api/docs/ |
| Health Check | https://dutchkem-trading-ai.onrender.com/health/ |

### Step 5.8: Free Tier Limits

- **750 hours/month** (spins down after 15min inactivity)
- **512 MB RAM** per service
- **PostgreSQL free for 90 days**, then $7/month
- **Redis free tier available**
- Automatic SSL certificates

---

## 6. Trading Operations

### 6.1: How Auto-Trading Works

The system uses **TRADING_MODE=full** which means:

1. **Every 60 seconds**, `run_v6_trading_cycle` task executes:
   - Fetches live market data from MT5 for all 5 symbols
   - Runs AI analysis (V6.5 orchestrator with 10 enhancements)
   - Generates multi-timeframe signals (M5, M15, M30, H1, H2, H4)
   - Calculates confluence scores
   - Applies risk management rules
   - Executes trades automatically if criteria are met

2. **Every 15 minutes**, signal generation tasks run for each symbol

3. **Every 5 minutes**, MT5 data sync and indicator calculations

4. **Every minute**, drawdown monitoring and performance calculation

5. **Daily at 03:00 UTC**, V6.5 self-optimization runs

### 6.2: Start Automatic Trading

Trading starts automatically when all services are running. To verify:

```powershell
# Check Celery Beat is scheduling tasks
docker compose -f docker-compose.yml logs celery-beat | findstr "v6-trading-cycle"

# Check Celery Worker is processing tasks
docker compose -f docker-compose.yml logs celery-worker | findstr "V6 cycle"
```

### 6.3: Pause Trading

To pause automatic trading without stopping the system:

1. Access Django Admin: http://localhost:8000/admin/ (or Render URL)
2. Go to **Django Celery Beat** → **Periodic Tasks**
3. Find **"run-v65-trading-cycle"**
4. Uncheck **"Enabled"**
5. Save

To resume: Re-enable the task.

### 6.4: Stop Trading Completely

```powershell
# Stop all services
docker compose -f docker-compose.yml down

# Or stop only the celery worker (keeps web accessible)
docker compose -f docker-compose.yml stop celery-worker celery-beat
```

### 6.5: Change Trading Mode

Edit `.env`:
```
TRADING_MODE=semi    # Requires manual approval for each trade
TRADING_MODE=manual  # No automatic trades
TRADING_MODE=full    # Fully automatic
```

Then restart:
```powershell
docker compose -f docker-compose.yml restart django celery-worker celery-beat
```

### 6.6: View Trade History

**Via Django Admin:**
1. Go to http://localhost:8000/admin/ (or Render URL)
2. Navigate to **Trading** → **Trades**
3. Filter by status, symbol, date

**Via API:**
```powershell
# Get auth token first
curl -X POST http://localhost:8000/api/auth/token/ -d "username=admin&password=yourpassword"

# Get trades
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/trades/
```

### 6.7: Check MT5 Connection Status

**Via API:**
```powershell
curl http://localhost:8000/health/
```

**Via Bridge directly:**
```powershell
# REST API health
curl http://localhost:8082/health

# Account info
curl http://localhost:8082/api/account

# Open positions
curl http://localhost:8082/api/positions
```

---

## 7. Monitoring & Dashboard

### 7.1: Real-Time Logs

```powershell
# Watch all services
docker compose -f docker-compose.yml logs -f

# Filter for trading activity
docker compose -f docker-compose.yml logs -f celery-worker | findstr "V6 cycle"

# Filter for errors
docker compose -f docker-compose.yml logs -f | findstr "ERROR"
```

### 7.2: Celery Flower (Task Monitor)

Add to `docker-compose.yml`:
```yaml
  flower:
    image: mher/flower:latest
    container_name: dutchkem-flower
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - redis
```

Access: http://localhost:5555

### 7.3: Performance Metrics

The system automatically calculates and caches:
- Daily P&L
- Win rate
- Profit factor
- Sharpe ratio
- Maximum drawdown
- Per-symbol performance

Access via API: `/api/analytics/performance/`

### 7.4: Risk Alerts

The system monitors:
- **Drawdown:** Alerts if equity drops below peak
- **Daily loss:** Stops trading if daily loss exceeds 2%
- **Position size:** Limits max position size to 2% of equity
- **Correlation:** Prevents over-correlated positions

### 7.5: Render Dashboard Monitoring

On Render, you can:
1. View **Logs** tab for each service
2. Check **Metrics** tab for CPU/Memory usage
3. Monitor **Events** tab for deployment history
4. Set up **Notifications** for service alerts

---

## 8. Troubleshooting

### 8.1: MT5 Bridge Not Connecting

**Symptoms:** "MT5 connection failed" in logs

**Solutions:**
1. Ensure MT5 terminal is running and logged in
2. Check MT5 → Tools → Options → Expert Advisors → "Allow Algo Trading" is enabled
3. Verify the bridge container can reach the host:
   ```powershell
   docker compose -f docker-compose.yml exec mt5-bridge ping host.docker.internal
   ```
4. Check port 1929 is not blocked by firewall

### 8.2: Celery Worker Not Starting

**Symptoms:** Tasks not executing

**Solutions:**
1. Check Redis is running:
   ```powershell
   docker compose -f docker-compose.yml exec redis redis-cli ping
   ```
2. Verify `CELERY_BROKER_URL` is set correctly
3. Check worker logs:
   ```powershell
   docker compose -f docker-compose.yml logs celery-worker
   ```

### 8.3: Database Connection Errors

**Solutions:**
1. Verify PostgreSQL is healthy:
   ```powershell
   docker compose -f docker-compose.yml exec db pg_isready -U dutchkem
   ```
2. Run migrations:
   ```powershell
   docker compose -f docker-compose.yml exec django python manage.py migrate
   ```

### 8.4: Django 502 Errors on Render

**Solutions:**
1. Check if service is spinning down (free tier inactivity)
2. Add a health check ping service
3. Upgrade to paid tier for always-on

### 8.5: Trades Not Executing

**Checklist:**
- [ ] MT5 terminal is running and logged in
- [ ] Algo trading is enabled in MT5
- [ ] MT5 Bridge container is healthy
- [ ] Celery Worker is processing tasks
- [ ] `TRADING_MODE=full` in `.env`
- [ ] Confluence score meets threshold (usually > 0.7)
- [ ] Risk limits not exceeded

---

## Quick Reference Commands

```powershell
# === LOCAL PRODUCTION ===

# Start everything
docker compose -f docker-compose.yml up -d

# Stop everything
docker compose -f docker-compose.yml down

# Restart everything
docker compose -f docker-compose.yml restart

# View logs
docker compose -f docker-compose.yml logs -f

# Check status
docker compose -f docker-compose.yml ps

# Access Django shell
docker compose -f docker-compose.yml exec django python manage.py shell

# Run migrations
docker compose -f docker-compose.yml exec django python manage.py migrate

# Create superuser
docker compose -f docker-compose.yml exec django python manage.py createsuperuser

# Collect static files
docker compose -f docker-compose.yml exec django python manage.py collectstatic --no-input


# === RENDER CLOUD ===

# Push changes
git add . && git commit -m "update" && git push

# View Render logs (via dashboard or CLI)
render logs -s dutchkem-trading-ai

# Restart service on Render (via dashboard)
# Go to Service → Manual Deploy → Clear build cache & deploy
```

---

## Security Notes

- `.env` files are in `.gitignore` and will NOT be pushed to GitHub
- MT5 credentials are stored locally only
- Render uses environment variables (encrypted at rest)
- All production services use SSL/HTTPS
- JWT tokens expire after 30 minutes
- Rate limiting: 1000 requests/hour for authenticated users

---

## Support

- **Health Check:** http://localhost:8000/health/ (local) or https://dutchkem-trading-ai.onrender.com/health/ (cloud)
- **API Documentation:** /api/docs/ endpoint
- **Logs:** Check Docker logs locally or Render dashboard for cloud

---

*This guide was generated for DutchKEM Trading AI v2.0 with V6.5 self-optimization engine.*
