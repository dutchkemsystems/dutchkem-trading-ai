# Dutchkem Trading AI — Render Deployment Guide

## Prerequisites
- GitHub account with the repository pushed to `dutchkemsystems/dutchkem-trading-ai`
- Render account (free at https://render.com)

---

## Step 1: Push to GitHub

```bash
git remote add origin https://github.com/dutchkemsystems/dutchkem-trading-ai.git
git push -u origin main
```

## Step 2: Create Render Account & Connect Repo

1. Go to https://dashboard.render.com
2. Sign up / log in with your GitHub account
3. Click **"New +"** → **"Web Service"**
4. Select the repository: `dutchkemsystems/dutchkem-trading-ai`

## Step 3: Configure Web Service

| Setting | Value |
|---------|-------|
| **Name** | `dutchkem-trading-ai` |
| **Runtime** | Python |
| **Plan** | Free |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `cd backend && python manage.py migrate --no-input && python manage.py collectstatic --no-input && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |

## Step 4: Set Environment Variables

In the Render dashboard, go to **Environment** tab and add:

| Key | Value |
|-----|-------|
| `DJANGO_SETTINGS_MODULE` | `config.settings_production` |
| `SECRET_KEY` | *(click "Generate" or paste a 50-char random string)* |
| `DEBUG` | `0` |
| `USE_SQLITE` | `0` |
| `ALLOWED_HOSTS` | `dutchkem-trading-ai.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | `https://dutchkem-trading-ai-frontend.onrender.com` |
| `SECURE_SSL_REDIRECT` | `True` |
| `SESSION_COOKIE_SECURE` | `True` |
| `CSRF_COOKIE_SECURE` | `True` |
| `MT5_HOST` | *(your MT5 bridge hostname)* |
| `MT5_PORT` | `443` |
| `MT5_WS_PORT` | `443` |
| `MT5_TIMEOUT` | `10` |
| `MT5_MAX_RETRIES` | `5` |
| `MT5_RETRY_DELAY` | `2.0` |

## Step 5: Create PostgreSQL Database

1. Click **"New +"** → **"PostgreSQL"**
2. **Name:** `dutchkem-db`
3. **Plan:** Free (90 days, then $7/month)
4. Once created, copy the **Internal Database URL**
5. Go back to your web service → **Environment** → add:
   - `DATABASE_URL` = *(pasted Internal Database URL)*

## Step 6: Create Redis Instance

1. Click **"New +"** → **"Redis"**
2. **Name:** `dutchkem-redis`
3. **Plan:** Free
4. Once created, copy the **Internal Redis URL**
5. Go back to your web service → **Environment** → add:
   - `REDIS_URL` = *(pasted Internal Redis URL)*
   - `CELERY_BROKER_URL` = *(same Redis URL)*

## Step 7: Deploy

Click **"Create Web Service"**. Render will:
1. Clone your repo
2. Install dependencies
3. Run migrations
4. Collect static files
5. Start Gunicorn

Monitor the deploy logs for errors.

## Step 8: Post-Deploy Setup

After the service is live:

1. Go to your backend service → **"Shell"** tab
2. Create a superuser:
   ```bash
   python manage.py createsuperuser --username admin --email admin@dutchkem.com
   ```
3. Verify health:
   ```bash
   curl https://dutchkem-trading-ai.onrender.com/health/
   ```

## Step 9: Deploy Frontend (Optional)

1. Click **"New +"** → **"Static Site"**
2. Connect the same repo
3. **Name:** `dutchkem-trading-ai-frontend`
4. **Build Command:** `cd frontend && npm install && npm run build`
5. **Publish Directory:** `frontend/build`
6. Add env var: `REACT_APP_API_URL` = `https://dutchkem-trading-ai.onrender.com`

---

## URLs After Deployment

| Service | URL |
|---------|-----|
| Backend API | `https://dutchkem-trading-ai.onrender.com` |
| Frontend | `https://dutchkem-trading-ai-frontend.onrender.com` |
| Admin Panel | `https://dutchkem-trading-ai.onrender.com/admin/` |
| Swagger Docs | `https://dutchkem-trading-ai.onrender.com/swagger/` |
| ReDoc | `https://dutchkem-trading-ai.onrender.com/redoc/` |
| Health Check | `https://dutchkem-trading-ai.onrender.com/health/` |
| Metrics | `https://dutchkem-trading-ai.onrender.com/metrics/` |

## Free Tier Limits
- 750 hours/month (spins down after 15 min inactivity)
- 512 MB RAM
- PostgreSQL free for 90 days, then $7/month
- Redis free tier included
- Automatic SSL

## Troubleshooting

### Build fails on `psycopg2`
Ensure `psycopg2-binary` is uncommented in `backend/requirements.txt` for PostgreSQL support.

### MT5 Bridge unreachable
Set `MT5_HOST` to your Cloudflare Tunnel URL or public MT5 bridge endpoint.

### Static files not loading
Run `python manage.py collectstatic --no-input` in the Render shell.
