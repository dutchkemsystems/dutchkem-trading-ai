# Railway Free-Tier Deployment Guide

## Overview

This guide deploys the Dutchkem Trading AI 2.0 application to Railway using the free tier with $5 credit.

## Free Tier Limits

- **$5 credit/month** (covers most small projects)
- **512 MB RAM** per service
- **1 GB storage** for PostgreSQL
- **1 GB storage** for Redis
- **100 GB bandwidth** per month
- **Custom domains** supported
- **Automatic SSL** certificates

## Prerequisites

1. Railway account (sign up at https://railway.app)
2. Railway CLI installed (`npm install -g @railway/cli`)
3. Git repository connected to GitHub

---

## Step-by-Step Deployment

### 1. Login to Railway

```powershell
railway login
```

This opens a browser window for authentication.

### 2. Create Backend Service

#### Option A: Via CLI

```powershell
cd C:\DUTCHKEM-TRADING-AI

# Create project
railway project create dutchkem-trading-ai

# Link to project
railway link

# Deploy backend
railway up
```

#### Option B: Via Dashboard (Recommended)

1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub Repo"
4. Select your repository: `DUTCHKEM-TRADING-AI`
5. Select branch: `feature/marketing-automation`
6. Railway will auto-detect the Dockerfile

### 3. Configure Backend Service

In the Railway dashboard:

1. Click on your backend service
2. Go to "Settings" tab
3. Under "Build", set:
   - **Dockerfile Path**: `dutchkem-trading-ai/backend/Dockerfile.railway`
4. Under "Deploy", set:
   - **Start Command**: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
   - **Healthcheck Path**: `/health/`

### 4. Add PostgreSQL Plugin

1. In your project dashboard, click "New" → "Database" → "PostgreSQL"
2. Railway auto-provisions PostgreSQL
3. The `DATABASE_URL` environment variable is automatically set

### 5. Add Redis Plugin

1. In your project dashboard, click "New" → "Database" → "Redis"
2. Railway auto-provisions Redis
3. The `REDIS_URL` environment variable is automatically set

### 6. Set Environment Variables

Go to your backend service → "Variables" tab → "Raw Editor" and add:

```bash
# Django Settings
DJANGO_SETTINGS_MODULE=config.settings_production
SECRET_KEY=your-secret-key-here
DEBUG=False

# Allowed Hosts
ALLOWED_HOSTS=dutchkem-trading-ai.up.railway.app

# CORS
CORS_ALLOWED_ORIGINS=https://dutchkem-trading-ai-frontend.up.railway.app

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# MT5 Bridge
MT5_BRIDGE_URL=https://your-cloudflare-tunnel-url.com
```

### 7. Deploy Backend

Railway auto-deploys on push. To manually deploy:

```powershell
railway up
```

### 8. Deploy Frontend

#### Create Frontend Service

1. In your project dashboard, click "New" → "Service"
2. Select "GitHub Repo" and select the same repository
3. In service settings, set:
   - **Root Directory**: `dutchkem-trading-ai/frontend`
   - **Dockerfile Path**: `dutchkem-trading-ai/frontend/Dockerfile.railway`

#### Set Frontend Environment Variables

```bash
REACT_APP_API_URL=https://dutchkem-trading-ai.up.railway.app
REACT_APP_WS_URL=wss://dutchkem-trading-ai.up.railway.app
```

### 9. Custom Domains (Optional)

1. Go to service settings
2. Click "Networking" → "Generate Domain"
3. Or add custom domain under "Custom Domain"

---

## URLs After Deployment

| Service | URL |
|---------|-----|
| Backend API | https://dutchkem-trading-ai.up.railway.app |
| Frontend | https://dutchkem-trading-ai-frontend.up.railway.app |
| Admin Panel | https://dutchkem-trading-ai.up.railway.app/admin/ |
| API Docs | https://dutchkem-trading-ai.up.railway.app/api/docs/ |

---

## MT5 Bridge via Cloudflare Tunnel

### 1. Install Cloudflare Tunnel

On your Windows machine running MT5:

```powershell
# Download cloudflared
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.msi" -OutFile "cloudflared.msi"

# Install
Start-Process msiexec.exe -ArgumentList '/i cloudflared.msi /quiet' -Wait
```

### 2. Create Tunnel

```powershell
# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create dutchkem-mt5

# Configure tunnel
cloudflared tunnel route dns dutchkem-mt5 mt5.dutchkem.com
```

### 3. Create Config File

Create `C:\Users\Lenovo\.cloudflared\config.yml`:

```yaml
tunnel: dutchkem-mt5
credentials-file: C:\Users\Lenovo\.cloudflared\<tunnel-id>.json

ingress:
  - hostname: mt5.dutchkem.com
    service: http://localhost:8080
  - service: http_status:404
```

### 4. Start Tunnel

```powershell
cloudflared tunnel run dutchkem-mt5
```

### 5. Update Environment Variables

Add to Railway:

```bash
MT5_BRIDGE_URL=https://mt5.dutchkem.com
```

---

## Free Tier Pricing Breakdown

| Resource | Free Allowance | Overage Cost |
|----------|----------------|--------------|
| RAM | 512 MB | $0.000463/MB/hour |
| CPU | 1 vCPU | $0.000463/vCPU/hour |
| PostgreSQL | 1 GB | $0.15/GB |
| Redis | 1 GB | $0.30/GB |
| Bandwidth | 100 GB | $0.15/GB |
| Build time | 500 hours | $0.000232/min |

### Estimated Monthly Cost

For a small trading app with moderate usage:
- Backend (256 MB RAM): ~$3.40/month
- PostgreSQL (500 MB): ~$0.75/month
- Redis (100 MB): ~$0.30/month
- Frontend (128 MB): ~$1.70/month
- **Total: ~$6.15/month** (slightly over $5 credit)

With optimizations and low traffic, you can stay within the $5 credit.

---

## Monitoring & Logs

### View Logs

```powershell
railway logs
```

### View Metrics

In Railway dashboard → Service → "Metrics" tab

### Health Check

Backend health endpoint: `GET /health/`

---

## Troubleshooting

### Build Fails

1. Check Dockerfile path in service settings
2. Ensure `requirements.txt` exists in backend directory
3. Check build logs for missing dependencies

### App Crashes on Start

1. Check environment variables are set correctly
2. Verify `DATABASE_URL` and `REDIS_URL` are connected
3. Check application logs for errors

### Static Files Not Loading

1. Ensure WhiteNoise is in `INSTALLED_APPS`
2. Verify `STATIC_ROOT` is set correctly
3. Run `collectstatic` manually if needed

### CORS Errors

1. Verify `CORS_ALLOWED_ORIGINS` includes frontend URL
2. Check `ALLOWED_HOSTS` includes backend URL

---

## Rollback

To rollback to a previous deployment:

```powershell
railway rollback
```

Or in dashboard → Deployments → Click "..." on previous deployment → "Redeploy"

---

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://railway.app/discord
- GitHub Issues: https://github.com/railwayapp/railway/issues

---

*Last updated: August 2026*
