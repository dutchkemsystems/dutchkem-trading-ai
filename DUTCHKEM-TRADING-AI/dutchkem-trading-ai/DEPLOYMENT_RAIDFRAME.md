# Dutchkem Trading AI — RaidFrame Deployment Guide

## Prerequisites
- GitHub account
- RaidFrame account (https://raidframe.com)
- Node.js 20+ installed locally

## Step 1: Install RaidFrame CLI

```bash
npm install -g raidframe
```

## Step 2: Login to RaidFrame

```bash
rf login
```

## Step 3: Initialize Your Project

```bash
cd C:\DUTCHKEM-TRADING-AI\dutchkem-trading-ai
rf init
```

Select:
- Framework: Django
- Database: PostgreSQL (managed)
- Redis: Yes (managed)

## Step 4: Add Redis for Celery

```bash
rf add redis
```

## Step 5: Set Environment Variables

```bash
rf env set SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
rf env set DEBUG=False
rf env set DJANGO_SETTINGS_MODULE=config.settings_production
rf env set ALLOWED_HOSTS=your-app-name raidframe.app
rf env set CORS_ALLOWED_ORIGINS=https://your-app-name raidframe.app
rf env set CSRF_TRUSTED_ORIGINS=https://your-app-name raidframe.app
```

## Step 6: Deploy Backend

```bash
rf deploy --service backend
```

## Step 7: Run Migrations

```bash
rf run python manage.py migrate --noinput
```

## Step 8: Create Superuser

```bash
rf run python manage.py createsuperuser
```

## Step 9: Collect Static Files

```bash
rf run python manage.py collectstatic --noinput
```

## Step 10: Deploy Frontend

```bash
cd frontend
npm install
npm run build
rf deploy --service frontend
```

## Step 11: Add Background Worker (Celery)

```bash
rf service create worker --command "celery -A config worker -l info --concurrency=2"
```

## Step 12: Add Celery Beat (Scheduled Tasks)

```bash
rf service create beat --command "celery -A config beat -l info"
```

## Step 13: Add Custom Domain (Optional)

```bash
rf domain add yourdomain.com
```

Then update DNS:
```
A Record: @ → RaidFrame IP
CNAME: www → your-app-name raidframe.app
```

## Step 14: Update Production Settings

Update `backend/config/settings_production.py` with your RaidFrame environment:

```python
import os
import dj_database_url

SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

DATABASES = {
    "default": dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Redis from RaidFrame
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# CORS
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
CORS_ALLOW_CREDENTIALS = True

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
```

## Verification Checklist

After deployment, verify:

1. **Web App**: https://your-app-name raidframe.app → Loads login page
2. **Admin**: https://your-app-name raidframe.app/admin/ → Admin login works
3. **API**: https://your-app-name raidframe.app/api/v1/ → API responds
4. **WebSocket**: wss://your-app-name raidframe.app/ws/market-data/EURUSD/ → Connects
5. **Worker**: Celery worker is running (check logs)
6. **Database**: PostgreSQL is connected (check health)

## Troubleshooting

### Check Logs
```bash
rf logs --service backend
rf logs --service worker
```

### Check Status
```bash
rf status
```

### Restart Services
```bash
rf restart --service backend
rf restart --service worker
```

### Enter Shell
```bash
rf shell --service backend
```

## Cost Estimate

| Service | Free Tier | Paid (if needed) |
|---------|-----------|------------------|
| Web App | Always-on, 256MB | $5/mo for 512MB |
| PostgreSQL | Managed, always-on | $5/mo for more storage |
| Redis | Included | $5/mo for more memory |
| Worker | Always-on | $5/mo for more CPU |
| Beat | Always-on | $5/mo for more CPU |
| **Total** | **$0/month** | **$20/month** |

## Next Steps After Deployment

1. Train ML models: `rf run python ml/training/train_lstm.py`
2. Configure MT5 connection in settings
3. Set up Korapay API keys
4. Deploy EA to MT5
5. Monitor performance in Grafana
