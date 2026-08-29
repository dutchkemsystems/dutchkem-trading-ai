# Dutchkem Trading AI 2.0 — Render Free-Tier Deployment Guide

> Complete step-by-step instructions for deploying the full stack on Render's free tier.

---

## Prerequisites

- GitHub repository pushed to `feature/marketing-automation` branch
- Render account at [render.com](https://render.com) (free tier)
- Cloudflare account (for MT5 Bridge Tunnel)

---

## Step 1: Create PostgreSQL Database

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **PostgreSQL**
3. Settings:
   - **Name:** `dutchkem-db`
   - **Database:** `dutchkem_trading`
   - **Plan:** Free
   - **IP Allow List:** `0.0.0.0/0` (or leave empty — Render handles internal networking)
4. Click **Create Database**
5. Wait for status to become **Available**
6. Copy the **Internal Database URL** (you'll need it later, or it auto-links via `render.yaml`)

---

## Step 2: Create Redis Instance

1. In Render Dashboard, click **New +** → **Redis**
2. Settings:
   - **Name:** `dutchkem-redis`
   - **Plan:** Free
   - **IP Allow List:** `0.0.0.0/0`
3. Click **Create Redis Instance**
4. Wait for status to become **Available**

---

## Step 3: Deploy Backend (Django + Gunicorn)

### Option A: Using `render.yaml` (Blueprints) — Recommended

1. In Render Dashboard, click **New +** → **Blueprint**
2. Connect your GitHub repository (`DUTCHKEM-TRADING-AI`)
3. Render will detect `render.yaml` at the repo root
4. Review the services it will create:
   - `dutchkem-trading-ai` (Web Service — Django backend)
   - `dutchkem-trading-ai-frontend` (Static Site — React frontend)
   - `dutchkem-db` (PostgreSQL)
   - `dutchkem-redis` (Redis)
5. Click **Apply** to create all resources

### Option B: Manual Setup

If not using Blueprints, create each service manually:

1. Click **New +** → **Web Service**
2. Connect GitHub repo `DUTCHKEM-TRADING-AI`
3. Settings:
   - **Name:** `dutchkem-trading-ai`
   - **Runtime:** Python
   - **Plan:** Free
   - **Build Command:**
     ```
     cd dutchkem-trading-ai/backend && pip install -r requirements.txt && python manage.py collectstatic --no-input
     ```
   - **Start Command:**
     ```
     cd dutchkem-trading-ai/backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
     ```
   - **Health Check Path:** `/health/`
   - **Auto Deploy:** Yes

4. Add Environment Variables:
   | Key | Value |
   |-----|-------|
   | `DJANGO_SETTINGS_MODULE` | `config.settings_production` |
   | `SECRET_KEY` | *(use Render's "Generate" button)* |
   | `DATABASE_URL` | *(link to dutchkem-db — use Internal URL)* |
   | `REDIS_URL` | *(link to dutchkem-redis — use Internal URL)* |
   | `ALLOWED_HOSTS` | `dutchkem-trading-ai.onrender.com` |
   | `CORS_ALLOWED_ORIGINS` | `https://dutchkem-trading-ai-frontend.onrender.com` |
   | `SECURE_SSL_REDIRECT` | `True` |
   | `SESSION_COOKIE_SECURE` | `True` |
   | `CSRF_COOKIE_SECURE` | `True` |

5. Click **Create Web Service**

---

## Step 4: Deploy Frontend (React Static Site)

### Option A: Via `render.yaml` Blueprint (auto-created in Step 3)

The frontend static site is created automatically.

### Option B: Manual Setup

1. Click **New +** → **Static Site**
2. Connect GitHub repo `DUTCHKEM-TRADING-AI`
3. Settings:
   - **Name:** `dutchkem-trading-ai-frontend`
   - **Plan:** Free
   - **Build Command:**
     ```
     cd dutchkem-trading-ai/frontend && npm install && npm run build
     ```
   - **Publish Directory:**
     ```
     dutchkem-trading-ai/frontend/build
     ```
4. Add Environment Variable:
   | Key | Value |
   |-----|-------|
   | `REACT_APP_API_URL` | `https://dutchkem-trading-ai.onrender.com` |
5. Add **Rewrite Rule:**
   - **Source:** `/*`
   - **Destination:** `/index.html`
6. Click **Create Static Site**

---

## Step 5: Run Database Migrations

After the backend deploys successfully:

1. Go to the `dutchkem-trading-ai` web service
2. Click **Shell** tab (or use Render's SSH)
3. Run:
   ```bash
   cd dutchkem-trading-ai/backend
   python manage.py migrate --no-input
   python manage.py createsuperuser
   ```

---

## Step 6: Set Up MT5 Bridge via Cloudflare Tunnel

The MT5 Bridge runs on your local Windows machine and exposes the MetaTrader 5 terminal to the cloud backend.

### 6.1 Install Cloudflare Tunnel (on your Windows machine)

```powershell
# Download cloudflared
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "C:\cloudflared.exe"
```

### 6.2 Start MT5 Bridge

```powershell
# Start the MCP bridge server (from the project)
cd C:\DUTCHKEM-TRADING-AI\dutchkem-trading-ai\mcp-servers\synx-mt5
python mcp_service.py
```

### 6.3 Create Cloudflare Tunnel

```powershell
# Authenticate with Cloudflare (first time only)
C:\cloudflared.exe tunnel login

# Create a named tunnel
C:\cloudflared.exe tunnel create dutchkem-mt5

# Route DNS
C:\cloudflared.exe tunnel route dns dutchkem-mt5 mt5.dutchkem.com

# Run the tunnel (pointing to local MCP bridge port 8080)
C:\cloudflared.exe tunnel run --url http://localhost:8080 dutchkem-mt5
```

### 6.4 Configure Backend to Use Tunnel

Set the `MT5_MCP_URL` environment variable in Render:

| Key | Value |
|-----|-------|
| `MT5_MCP_URL` | `https://mt5.dutchkem.com` |

---

## Step 7: Verify Deployment

### Backend Health Check
```
https://dutchkem-trading-ai.onrender.com/health/
```

### Backend Admin
```
https://dutchkem-trading-ai.onrender.com/admin/
```

### Frontend
```
https://dutchkem-trading-ai-frontend.onrender.com
```

### API Root
```
https://dutchkem-trading-ai.onrender.com/api/v1/
```

---

## Post-Deployment Checklist

- [ ] Backend health check returns 200
- [ ] Frontend loads and connects to API
- [ ] User registration and login work
- [ ] Database migrations ran successfully
- [ ] Superuser created
- [ ] MT5 Bridge tunnel is active
- [ ] SSL certificates are valid (automatic on Render)
- [ ] CORS is configured correctly (frontend ↔ backend)
- [ ] Celery workers are processing tasks (if Redis is linked)

---

## Render Free-Tier Limitations

| Resource | Free Tier Limit |
|----------|----------------|
| Web Services | 750 hours/month |
| Static Sites | 100 GB bandwidth/month |
| PostgreSQL | 90 days, 1 GB storage |
| Redis | 30 days, 25 MB memory |
| Sleep After | 15 min inactivity |
| Spin Up | ~30-50 seconds cold start |

> **Note:** Render free-tier services spin down after 15 minutes of inactivity. The first request after idle will take 30-50 seconds. Consider upgrading to a paid plan for production use.

---

## Troubleshooting

### Build Fails
- Check build logs in Render Dashboard → Service → Logs
- Ensure `requirements.txt` is in `dutchkem-trading-ai/backend/`
- Verify Python version matches `runtime.txt`

### Database Connection Error
- Ensure `DATABASE_URL` uses the **Internal URL** (not External)
- Check that `dj-database-url` is in `requirements.txt`

### CORS Errors
- Verify `CORS_ALLOWED_ORIGINS` includes the frontend URL
- Check that `corsheaders` is in `INSTALLED_APPS`

### Static Files Not Loading
- Run `python manage.py collectstatic --no-input` via Shell
- Verify WhiteNoise middleware is in `MIDDLEWARE` list

---

## Files Modified for Render

| File | Purpose |
|------|---------|
| `render.yaml` | Render Blueprint (infrastructure as code) |
| `backend/build.sh` | Build script for Render |
| `frontend/.env.render` | Frontend env vars for Render |
| `backend/config/settings_production.py` | Updated for Render hostname detection |
| `RENDER_DEPLOY.md` | This deployment guide |
