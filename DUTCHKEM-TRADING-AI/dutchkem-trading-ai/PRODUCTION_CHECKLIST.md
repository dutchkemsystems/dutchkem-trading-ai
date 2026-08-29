# Dutchkem Trading AI — Production Checklist

## 1. Environment Configuration

### Backend (.env)
- [ ] `DJANGO_SECRET_KEY` — Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_ALLOWED_HOSTS` — Set production domain(s)
- [ ] `DATABASE_URL` — PostgreSQL production connection string
- [ ] `REDIS_URL` — Production Redis for Celery/caching
- [ ] `CELERY_BROKER_URL` — Redis or RabbitMQ broker
- [ ] `CORS_ALLOWED_ORIGINS` — Production frontend domain
- [ ] `KORAPAY_SECRET_KEY` — Live payment gateway key
- [ ] `KORAPAY_PUBLIC_KEY` — Live payment gateway public key
- [ ] `MT5_API_KEY` — MetaTrader 5 connection credentials
- [ ] `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- [ ] `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (if using S3 for file storage)

### Frontend (.env)
- [ ] `REACT_APP_API_URL` — Production API endpoint (e.g., `https://api.dutchkem.com/api/v1`)
- [ ] `REACT_APP_WS_URL` — Production WebSocket endpoint

## 2. Security Hardening

- [ ] Change `DJANGO_SECRET_KEY` from default
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Configure `SECURE_SSL_REDIRECT=True`
- [ ] Set `SESSION_COOKIE_SECURE=True`
- [ ] Set `CSRF_COOKIE_SECURE=True`
- [ ] Set `SECURE_HSTS_SECONDS=31536000`
- [ ] Set `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`
- [ ] Set `SECURE_HSTS_PRELOAD=True`
- [ ] Set `SECURE_BROWSER_XSS_FILTER=True`
- [ ] Set `SECURE_CONTENT_TYPE_NOSNIFF=True`
- [ ] Enable `MFA` for all admin accounts
- [ ] Configure CORS to allow only production frontend domain
- [ ] Review and rotate all API keys and secrets

## 3. Database

- [ ] Run `python manage.py migrate` on production database
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Load initial data (symbols, indicators, timeframes)
- [ ] Verify database backups are configured
- [ ] Set up automated daily backups

## 4. Infrastructure

- [ ] Configure reverse proxy (Nginx/Caddy) with SSL
- [ ] Set up SSL certificates (Let's Encrypt or commercial)
- [ ] Configure static file serving (Whitenoise or CDN)
- [ ] Configure media file storage (S3 or local with backup)
- [ ] Set up Redis for Celery workers and caching
- [ ] Configure Celery workers and beat scheduler
- [ ] Set up process manager (systemd, supervisor, or Docker)

## 5. Build & Deploy

### Frontend
```bash
cd frontend
npm install
npm run build
# Deploy build/ directory to hosting service
```

### Backend
```bash
cd backend
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
# Start with gunicorn: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

## 6. Monitoring & Logging

- [ ] Configure structured logging (JSON format)
- [ ] Set up error tracking (Sentry or equivalent)
- [ ] Configure uptime monitoring
- [ ] Set up performance monitoring (New Relic, Datadog)
- [ ] Configure log aggregation
- [ ] Set up alerts for critical failures

## 7. Performance

- [ ] Enable database query caching
- [ ] Configure Redis caching for frequently accessed data
- [ ] Enable gzip/brotli compression on reverse proxy
- [ ] Optimize static file delivery (CDN, cache headers)
- [ ] Configure database connection pooling
- [ ] Review and optimize slow queries

## 8. Testing

- [ ] Run full backend test suite: `python manage.py test`
- [ ] Run frontend build verification: `npm run build`
- [ ] Verify all API endpoints respond correctly
- [ ] Test authentication flow (login, register, MFA)
- [ ] Test payment integration (Korapay sandbox → live)
- [ ] Test MT5 connection and order execution
- [ ] Load test critical endpoints

## 9. Domain & DNS

- [ ] Configure DNS records for production domain
- [ ] Set up subdomains (api.dutchkem.com, www.dutchkem.com)
- [ ] Verify SSL certificate covers all subdomains
- [ ] Configure CDN if using external CDN provider

## 10. Backup & Recovery

- [ ] Automated database backups (daily minimum)
- [ ] Backup retention policy configured
- [ ] Documented recovery procedure
- [ ] Test restore from backup
- [ ] File storage backup (S3 versioning or local backup)

## 11. Compliance

- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] KYC/AML procedures documented
- [ ] Data retention policy defined
- [ ] GDPR compliance (if applicable)

## 12. Go-Live

- [ ] Final security audit completed
- [ ] All team members have access credentials
- [ ] Support email/helpdesk configured
- [ ] Status page created
- [ ] Emergency rollback procedure documented
- [ ] On-call rotation established
