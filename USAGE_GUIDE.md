# =============================================================================
# Dutchkem Trading AI — Complete Usage Guide
# =============================================================================
# Version: 1.0 | Updated: 2026-09-01
# MT5 Account: 161704951 | Server: Exness-MT5Real21
# =============================================================================

## Table of Contents

1. [Local Production Setup](#1-local-production-setup)
2. [Cloud Deployment on Render](#2-cloud-deployment-on-render)
3. [Trading Operations](#3-trading-operations)
4. [Monitoring & Administration](#4-monitoring--administration)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Local Production Setup

### Prerequisites

- **Docker Desktop** (required for PostgreSQL, Redis, and MT5 Bridge)
- **Python 3.12+** (for local Django development without Docker)
- **MT5 Terminal** running on Windows with Exness-MT5Real21 server

### Step 1: Install Docker Desktop

Since Docker is not currently installed, follow these steps:

#### Download Docker Desktop
1. Visit: https://www.docker.com/products/docker-desktop/
2. Click **"Download for Windows"**
3. Run the installer (`Docker Desktop Installer.exe`)
4. Follow the installation wizard
5. **Important**: Ensure "Use WSL 2 instead of Hyper-V" is checked during installation

#### Post-Installation Steps
1. **Restart your computer** after installation
2. Open Docker Desktop and wait for it to start (whale icon in system tray turns solid)
3. Open a new terminal and verify Docker is running:
   ```bash
   docker --version
   docker compose version
   ```

#### Enable WSL2 (if not already enabled)
```powershell
# Run in PowerShell as Administrator
wsl --install
# Restart computer
wsl --set-default-version 2
```

### Step 2: Start All Services

```bash
# Navigate to project directory
cd C:\DUTCHKEM-TRADING-AI

# Start the full stack (PostgreSQL, Redis, MT5 Bridge, Django, Celery)
docker compose -f docker-compose.full.yml up -d

# Check all services are running
docker compose -f docker-compose.full.yml ps
```

### Step 3: Create Database & Superuser

```bash
# Wait for PostgreSQL to be healthy (check with: docker compose -f docker-compose.full.yml ps)

# Run migrations
docker compose -f docker-compose.full.yml exec django python manage.py migrate --no-input

# Create superuser for admin access
docker compose -f docker-compose.full.yml exec django python manage.py createsuperuser --username admin --email admin@dutchkem.com
```

### Step 4: Verify Local Deployment

| Service | URL | Status Check |
|---------|-----|--------------|
| Django Backend | http://localhost:8000 | http://localhost:8000/health/ |
| MT5 Bridge REST | http://localhost:8082 | http://localhost:8082/health |
| MT5 Bridge WebSocket | ws://localhost:8081 | Connection test |
| Admin Panel | http://localhost:8000/admin | Login with superuser |
| API Docs | http://localhost:8000/swagger | Swagger UI |

### Step 5: Start Automatic Trading

Trading starts automatically when `TRADING_MODE=full` is set in `.env` and Celery Beat is running.

```bash
# Verify trading is active
docker compose -f docker-compose.full.yml logs celery-beat | grep "run-v6-trading-cycle"

# Check trading logs
docker compose -f docker-compose.full.yml logs celery-worker | tail -50
```

---

## 2. Cloud Deployment on Render

### Prerequisites
- GitHub repository pushed to `dutchkemsystems/dutchkem-trading-ai`
- Render account (https://dashboard.render.com)
- Exness MT5 terminal running on your local machine (for MT5 bridge connection)

### Step 1: Push to GitHub

```bash
cd C:\DUTCHKEM-TRADING-AI
git add .
git commit -m "Configure production environment and render.yaml"
git push origin main
```

### Step 2: Deploy on Render

1. **Log in** to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"** (this uses `render.yaml` automatically)
3. Select your repository: `dutchkemsystems/dutchkem-trading-ai`
4. Render will create:
   - PostgreSQL database (`dutchkem-db`)
   - Redis instance (`dutchkem-redis`)
   - Django web service (`dutchkem-trading-ai`)
   - Celery worker (`dutchkem-celery-worker`)
   - Celery beat (`dutchkem-celery-beat`)

### Step 3: Set Manual Environment Variables (sync: false)

After deployment, go to each service's **Environment** tab and set these variables manually:

#### For Django Web Service, Celery Worker, and Celery Beat:

| Variable | Value |
|----------|-------|
| `REDIS_URL` | *(from Render Redis dashboard → Internal URL)* |
| `CELERY_BROKER_URL` | *(same Redis URL)* |
| `MT5_HOST` | Your MT5 bridge hostname (see Step 4) |
| `MT5_LOGIN` | `161704951` |
| `MT5_PASSWORD` | `Christ@5436` |
| `MT5_SERVER` | `Exness-MT5Real21` |

### Step 4: Configure MT5 Bridge for Cloud

For Render cloud deployment, your MT5 terminal must be accessible remotely. Options:

#### Option A: Cloudflare Tunnel (Recommended)
1. Install Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
2. Run the tunnel exposing port 1929:
   ```bash
   cloudflared tunnel --url tcp://localhost:1929
   ```
3. Set `MT5_HOST` in Render to the tunnel URL

#### Option B: ngrok
1. Install ngrok: https://ngrok.com/
2. Run:
   ```bash
   ngrok tcp 1929
   ```
3. Set `MT5_HOST` in Render to the ngrok TCP address

#### Option C: Public IP
1. Configure your router to forward port 1929 to your machine
2. Set `MT5_HOST` to your public IP address

### Step 5: Create Superuser on Render

1. Go to your Django web service → **Shell** tab
2. Run:
   ```bash
   python manage.py createsuperuser --username admin --email admin@dutchkem.com
   ```

### Step 6: Verify Cloud Deployment

| Service | URL |
|---------|-----|
| Backend API | https://dutchkem-trading-ai.onrender.com |
| Admin Panel | https://dutchkem-trading-ai.onrender.com/admin/ |
| Swagger Docs | https://dutchkem-trading-ai.onrender.com/swagger/ |
| Health Check | https://dutchkem-trading-ai.onrender.com/health/ |

---

## 3. Trading Operations

### How Auto-Trading Works

The trading pipeline runs automatically via Celery Beat scheduler:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTOMATIC TRADING PIPELINE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Every 60 seconds (run-v6-trading-cycle):                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │ Market Data  │──▶│   Signals    │──▶│   Execute    │       │
│  │  Ingestion   │   │  Generation  │   │   Trades     │       │
│  └──────────────┘   └──────────────┘   └──────────────┘       │
│         │                  │                  │                  │
│         ▼                  ▼                  ▼                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐       │
│  │  Indicator   │   │    Risk      │   │    MT5       │       │
│  │ Calculation  │   │  Management  │   │   Bridge     │       │
│  └──────────────┘   └──────────────┘   └──────────────┘       │
│                                                                  │
│  Active Symbols: EURUSD, GBPUSD, USDJPY, AUDUSD, XAUUSD        │
│  Timeframes: M5, M15, M30, H1, H2, H4                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Trading Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `full` | Fully automatic trading | Production (current setting) |
| `semi` | Auto signals, manual execution | Testing/learning |
| `manual` | Signals only, no execution | Analysis only |
| `off` | Trading disabled | Maintenance |

### Start Automatic Trading

Trading starts automatically when the system is running with `TRADING_MODE=full`.

**Verify trading is active:**
```bash
# Check Celery Beat is scheduling trading cycles
docker compose -f docker-compose.full.yml logs celery-beat --tail=20

# Check Celery Worker is executing trades
docker compose -f docker-compose.full.yml logs celery-worker --tail=50

# Check MT5 Bridge connection
curl http://localhost:8082/health
```

### Pause Trading

To pause trading without stopping the system:

1. **Via Admin Panel:**
   - Go to http://localhost:8000/admin (or Render URL)
   - Navigate to **Django Celery Beat** → **Periodic Tasks**
   - Find `run-v6-trading-cycle` and uncheck **Enabled**
   - Save

2. **Via Environment Variable:**
   - Change `TRADING_MODE=off` in `.env`
   - Restart services: `docker compose -f docker-compose.full.yml restart django celery-worker`

### Stop Trading

To completely stop trading:

```bash
# Stop Celery Beat (stops all periodic tasks)
docker compose -f docker-compose.full.yml stop celery-beat

# Or stop the entire stack
docker compose -f docker-compose.full.yml down
```

### View Trade History

1. **Admin Panel:** http://localhost:8000/admin/trading/
2. **API Endpoint:** `GET /api/v1/trading/trades/`
3. **Database Query:**
   ```sql
   SELECT * FROM trading_trade ORDER BY created_at DESC LIMIT 100;
   ```

---

## 4. Monitoring & Administration

### Dashboard Access

| Interface | URL | Description |
|-----------|-----|-------------|
| Django Admin | http://localhost:8000/admin | Full system management |
| Swagger API | http://localhost:8000/swagger | Interactive API docs |
| ReDoc | http://localhost:8000/redoc | API documentation |
| Health Check | http://localhost:8000/health | System health status |
| Metrics | http://localhost:8000/metrics | System metrics |

### Check MT5 Connection Status

```bash
# Check MT5 Bridge health
curl http://localhost:8082/health

# Check MT5 Bridge logs
docker compose -f docker-compose.full.yml logs mt5-bridge --tail=50

# Verify MT5 credentials in logs
docker compose -f docker-compose.full.yml logs mt5-bridge | grep -i "login\|connected"
```

### Monitor System Logs

```bash
# View all logs
docker compose -f docker-compose.full.yml logs -f

# View specific service logs
docker compose -f docker-compose.full.yml logs -f celery-worker
docker compose -f docker-compose.full.yml logs -f django
docker compose -f docker-compose.full.yml logs -f celery-beat

# View trading-specific logs
docker compose -f docker-compose.full.yml logs celery-worker | grep -i "trade\|signal\|execute"
```

### Check Celery Task Status

1. **Admin Panel:** http://localhost:8000/admin/django_celery_results/chordcounter/
2. **Via Django Shell:**
   ```bash
   docker compose -f docker-compose.full.yml exec django python manage.py shell
   
   # Check active tasks
   from celery import current_app
   inspector = current_app.control.inspect()
   print(inspector.active())
   print(inspector.scheduled())
   ```

### Database Management

```bash
# Access PostgreSQL
docker compose -f docker-compose.full.yml exec db psql -U dutchkem -d dutchkem_trading

# Run migrations
docker compose -f docker-compose.full.yml exec django python manage.py migrate

# Create superuser
docker compose -f docker-compose.full.yml exec django python manage.py createsuperuser

# Dump database
docker compose -f docker-compose.full.yml exec db pg_dump -U dutchkem dutchkem_trading > backup.sql
```

---

## 5. Troubleshooting

### Common Issues

#### MT5 Bridge Not Connecting
```bash
# Check if MT5 terminal is running
# Verify port 1929 is open
netstat -an | findstr 1929

# Check MT5 Bridge logs
docker compose -f docker-compose.full.yml logs mt5-bridge

# Restart MT5 Bridge
docker compose -f docker-compose.full.yml restart mt5-bridge
```

#### Celery Worker Not Processing Tasks
```bash
# Check Redis connection
docker compose -f docker-compose.full.yml exec redis redis-cli ping

# Check Celery Worker status
docker compose -f docker-compose.full.yml logs celery-worker --tail=20

# Restart Celery Worker
docker compose -f docker-compose.full.yml restart celery-worker
```

#### Database Connection Issues
```bash
# Check PostgreSQL is running
docker compose -f docker-compose.full.yml ps db

# Check database health
docker compose -f docker-compose.full.yml exec db pg_isready -U dutchkem -d dutchkem_trading

# Restart PostgreSQL
docker compose -f docker-compose.full.yml restart db
```

#### Static Files Not Loading
```bash
# Rebuild and collect static files
docker compose -f docker-compose.full.yml exec django python manage.py collectstatic --no-input

# Rebuild Docker image
docker compose -f docker-compose.full.yml build --no-cache django
```

### Emergency Stop

If trading is causing losses and you need to stop immediately:

```bash
# Option 1: Stop all services
docker compose -f docker-compose.full.yml down

# Option 2: Stop only trading
docker compose -f docker-compose.full.yml stop celery-beat celery-worker

# Option 3: Disable trading via environment
# Edit .env: TRADING_MODE=off
# Then restart
docker compose -f docker-compose.full.yml restart
```

---

## Quick Reference Commands

```bash
# Start full stack
docker compose -f docker-compose.full.yml up -d

# Stop full stack
docker compose -f docker-compose.full.yml down

# View status
docker compose -f docker-compose.full.yml ps

# View logs (all services)
docker compose -f docker-compose.full.yml logs -f

# Restart a specific service
docker compose -f docker-compose.full.yml restart [service-name]

# Access Django shell
docker compose -f docker-compose.full.yml exec django python manage.py shell

# Access database
docker compose -f docker-compose.full.yml exec db psql -U dutchkem -d dutchkem_trading
```

---

**Security Notes:**
- Never commit `.env` files to Git (already in `.gitignore`)
- Use strong, unique `SECRET_KEY` values
- Enable `SECURE_SSL_REDIRECT=True` in production
- Regularly rotate MT5 passwords
- Monitor trading logs for suspicious activity
