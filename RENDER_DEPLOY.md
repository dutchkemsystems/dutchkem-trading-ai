# Dutchkem Trading AI 2.0 — Render Free Tier Deployment Guide

## Prerequisites
- GitHub account with the repository pushed
- Render account (free at https://render.com)

## Step 1: Deploy Backend

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo: `dutchkemsystems/dutchkem-trading-ai`
4. Configure:
   - **Name:** `dutchkem-trading-ai`
   - **Runtime:** Python
   - **Build Command:** `cd dutchkem-trading-ai/backend && pip install -r requirements.txt && python manage.py collectstatic --no-input`
   - **Start Command:** `cd dutchkem-trading-ai/backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
   - **Plan:** Free
5. Add Environment Variables:
   ```
   DJANGO_SETTINGS_MODULE=config.settings_production
   SECRET_KEY=(generate a new one)
   DEBUG=False
   ALLOWED_HOSTS=dutchkem-trading-ai.onrender.com
   CORS_ALLOWED_ORIGINS=https://dutchkem-trading-ai-frontend.onrender.com
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```
6. Click **"Create Web Service"**

## Step 2: Create PostgreSQL Database

1. Click **"New +"** → **"PostgreSQL"**
2. Configure:
   - **Name:** `dutchkem-db`
   - **Plan:** Free (90 days)
3. Copy the **Internal Database URL**
4. Add it to your web service as `DATABASE_URL`

## Step 3: Deploy Frontend

1. Click **"New +"** → **"Static Site"**
2. Connect the same GitHub repo
3. Configure:
   - **Name:** `dutchkem-trading-ai-frontend`
   - **Build Command:** `cd dutchkem-trading-ai/frontend && npm install && npm run build`
   - **Publish Directory:** `dutchkem-trading-ai/frontend/build`
   - **Plan:** Free
4. Add Environment Variable:
   ```
   REACT_APP_API_URL=https://dutchkem-trading-ai.onrender.com
   ```
5. Click **"Create Static Site"**

## Step 4: Run Migrations

After backend deploys:
1. Go to your backend service → **"Shell"** tab
2. Run:
   ```bash
   python manage.py migrate --no-input
   python manage.py createsuperuser --username admin --email admin@dutchkem.com
   ```

## Step 5: URLs After Deployment

| Service | URL |
|---------|-----|
| Backend API | https://dutchkem-trading-ai.onrender.com |
| Frontend | https://dutchkem-trading-ai-frontend.onrender.com |
| Admin Panel | https://dutchkem-trading-ai.onrender.com/admin/ |
| Swagger Docs | https://dutchkem-trading-ai.onrender.com/swagger/ |
| Health Check | https://dutchkem-trading-ai.onrender.com/health/ |

## Free Tier Limits
- 750 hours/month (spins down after 15min inactivity)
- 512 MB RAM
- PostgreSQL free for 90 days, then $7/month
- Automatic SSL

## MT5 Bridge Setup

See `mcp-servers/synx-mt5/cloudflare-tunnel.md` for MT5 bridge configuration.
