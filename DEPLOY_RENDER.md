# Dutchkem Trading AI — Render Deployment Guide

## Overview: What You're Deploying

| Service | Type | Purpose |
|---------|------|---------|
| `dutchkem-backend` | Web Service | Django REST API + MT5 Bridge |
| `dutchkem-worker` | Background Worker | Celery background tasks |
| `dutchkem-beat` | Cron Job | Celery periodic scheduler |
| `dutchkem-redis` | Redis | Cache + Celery broker |
| `dutchkem-frontend` | Web Service | Next.js + Better Auth |

**Database:** Layerbase Cloud PostgreSQL (already provisioned, external)  
**No need for Render PostgreSQL** — everything goes to Layerbase.

---

## STEP 1: Create Redis

1. Go to https://dashboard.render.com/
2. Click **"New +"** button (top left)
3. Select **"Redis"**
4. Fill in:
   - **Name:** `dutchkem-redis`
   - **Region:** Oregon (US West) or closest to you
   - **Plan:** Free
5. Click **"Create Redis"**
6. Wait for it to show **"Available"** (takes ~30 seconds)
7. **Copy the Internal Redis URL** — it looks like:
   ```
   redis://red-xxxxxxxxxxxx:6379
   ```
   Save this — you'll need it for all other services.

---

## STEP 2: Create Django Backend

1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repo:
   - **Repository:** `dutchkemsystems/dutchkem-trading-ai`
   - **Branch:** `main`
3. Fill in:
   - **Name:** `dutchkem-backend`
   - **Runtime:** `Docker`
   - **Region:** Oregon (same as Redis)
   - **Plan:** Free
4. **Before clicking Create**, scroll down to **"Environment Variables"** section
5. Add these env vars (click "Add Environment Variable" for each):

```
SECRET_KEY = twPP1WYr34W6v5vO09UJttOspS2qol2PQiAMIBcWUHv4VcKo8y5FxxZ0g01D-Ied_hA
DEBUG = 0
DJANGO_SETTINGS_MODULE = config.settings_production
USE_SQLITE = 0
DATABASE_URL = postgresql://postgres:7MoevMEs2IIX9e01TmRLP1Fc@dutchkem-trading-ai-slim-drain-pooler.cloud.layerbase.dev/dutchkem_trading_ai?sslmode=require
REDIS_URL = redis://red-xxxxxxxxxxxx:6379
CELERY_BROKER_URL = redis://red-xxxxxxxxxxxx:6379/1
TRADING_ENGINE = v6.5
V65_ENABLED = true
TRADING_MODE = semi
VIRTUAL_ACCOUNT_BALANCE = 10.0
MT5_HOST = localhost
MT5_PORT = 8082
MT5_TIMEOUT = 10
MT5_MAX_RETRIES = 5
MT5_RETRY_DELAY = 2.0
MT5_LOGIN = 161704951
MT5_PASSWORD = [YOUR_MT5_PASSWORD]
MT5_SERVER = Exness-MT5Real21
ALLOWED_HOSTS = dutchkem-backend.onrender.com
CORS_ALLOWED_ORIGINS = https://dutchkem-frontend.onrender.com
CSRF_TRUSTED_ORIGINS = https://dutchkem-frontend.onrender.com
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

> **IMPORTANT:** Replace `redis://red-xxxxxxxxxxxx:6379` with the actual Redis URL from Step 1.  
> Replace `[YOUR_MT5_PASSWORD]` with your real MT5 password.

6. Click **"Create Web Service"**
7. Wait for the first deploy to complete (~3-5 minutes)

---

## STEP 3: Create Celery Worker

1. Click **"New +"** → **"Background Worker"**
2. Connect the same GitHub repo:
   - **Repository:** `dutchkemsystems/dutchkem-trading-ai`
   - **Branch:** `main`
3. Fill in:
   - **Name:** `dutchkem-worker`
   - **Runtime:** `Docker`
   - **Region:** Oregon
   - **Plan:** Free
4. **Start Command:** Leave blank (will use Dockerfile CMD)
   - Or set to: `celery -A config.celery worker -l info -Q default,market_data,trading,signals,backtesting --concurrency=2`
5. Add the **SAME environment variables** as Step 2 (copy all of them)
6. Click **"Create Background Worker"**

---

## STEP 4: Create Celery Beat (Scheduler)

1. Click **"New +"** → **"Cron Job"**
2. Connect the same GitHub repo:
   - **Repository:** `dutchkemsystems/dutchkem-trading-ai`
   - **Branch:** `main`
3. Fill in:
   - **Name:** `dutchkem-beat`
   - **Runtime:** `Docker`
   - **Region:** Oregon
   - **Plan:** Free
   - **Schedule:** `*/5 * * * *` (every 5 minutes)
   - **Start Command:** `celery -A config.celery beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`
4. Add the **SAME environment variables** as Step 2
5. Click **"Create Cron Job"**

---

## STEP 5: Create Next.js Frontend

1. Click **"New +"** → **"Web Service"**
2. Connect the same GitHub repo:
   - **Repository:** `dutchkemsystems/dutchkem-trading-ai`
   - **Branch:** `main`
3. Fill in:
   - **Name:** `dutchkem-frontend`
   - **Runtime:** `Docker`
   - **Region:** Oregon
   - **Plan:** Free
   - **Root Directory:** `frontend`
4. Add these env vars:

```
BETTER_AUTH_DATABASE_URL = postgresql://postgres:7MoevMEs2IIX9e01TmRLP1Fc@dutchkem-trading-ai-slim-drain-pooler.cloud.layerbase.dev/dutchkem_trading_ai?sslmode=require
BETTER_AUTH_SECRET = dutchkem-trading-ai-better-auth-secret-2026
BETTER_AUTH_URL = https://dutchkem-frontend.onrender.com
NEXT_PUBLIC_APP_URL = https://dutchkem-frontend.onrender.com
NEXT_PUBLIC_API_URL = https://dutchkem-backend.onrender.com
```

5. Click **"Create Web Service"**

---

## STEP 6: Update Backend CORS After Frontend Deploys

Once the frontend is live (URL: `https://dutchkem-frontend.onrender.com`):

1. Go to `dutchkem-backend` service → **Environment** tab
2. Update these env vars:
   ```
   ALLOWED_HOSTS = dutchkem-backend.onrender.com
   CORS_ALLOWED_ORIGINS = https://dutchkem-frontend.onrender.com
   CSRF_TRUSTED_ORIGINS = https://dutchkem-frontend.onrender.com
   ```
3. The service will auto-redeploy

---

## STEP 7: Verify Everything

### Backend Health
```bash
curl https://dutchkem-backend.onrender.com/health/
curl https://dutchkem-backend.onrender.com/api/ml/v65/status/
curl https://dutchkem-backend.onrender.com/api/accounts/trading-accounts/
```

### Django Admin
Open: https://dutchkem-backend.onrender.com/admin/
- Username: `admin`
- Password: `Dutchkem@2026!`

### Frontend
Open: https://dutchkem-frontend.onrender.com/
- Try signing up with email/password
- Try signing in

### Better Auth API
```bash
curl https://dutchkem-frontend.onrender.com/api/auth/sign-in/email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

---

## Architecture Diagram

```
┌─────────────────────┐     ┌─────────────────────┐
│   Next.js Frontend  │────▶│   Django Backend     │
│   (dutchkem-        │     │   (dutchkem-         │
│    frontend)        │     │    backend)           │
│                     │     │                      │
│  Better Auth        │     │  REST API            │
│  /api/auth/*        │     │  /api/ml/*           │
└────────┬────────────┘     │  /api/trading/*      │
         │                  │  /admin/*            │
         │                  └────────┬─────────────┘
         │                           │
         ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Layerbase Cloud    │     │  Layerbase Cloud    │
│  PostgreSQL         │◀───▶│  PostgreSQL         │
│  (Better Auth +     │     │  (Django models +   │
│   Django tables)    │     │   Trading data)     │
└─────────────────────┘     └─────────────────────┘
                                     │
                                     ▼
                            ┌─────────────────────┐
                            │  Redis (Render Free) │
                            │  Cache + Celery      │
                            └─────────────────────┘
```

---

## Troubleshooting

### "Exited with status 128"
- This was caused by Windows CRLF in shell scripts
- Fixed: Django now uses `start.py` (Python entrypoint)
- If it still happens, check Render logs for the actual error

### "ModuleNotFoundError"
- Check that all env vars are set correctly
- Specifically `DATABASE_URL` and `SECRET_KEY`

### "Connection refused" to database
- Verify Layerbase DB is running: `lbase cloud ls`
- Check the connection string has `?sslmode=require`

### Frontend can't reach backend
- Check `NEXT_PUBLIC_API_URL` is set to the backend URL
- Check backend `CORS_ALLOWED_ORIGINS` includes the frontend URL

### MT5 bridge not connecting
- MT5 bridge runs locally, not on Render
- Set up Cloudflare tunnel on your local machine
- Update `MT5_HOST` with the tunnel URL
