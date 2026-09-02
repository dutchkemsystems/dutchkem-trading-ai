#!/bin/sh
set -e

echo "=== Dutchkem Trading AI — Starting ==="

# Step 1: Migrations
echo "[1/3] Running migrations..."
python manage.py migrate --no-input 2>&1 || echo "WARN: Some migrations failed, continuing..."

# Step 2: Collect static
echo "[2/3] Collecting static files..."
python manage.py collectstatic --no-input 2>&1 || echo "WARN: collectstatic failed, continuing..."

# Step 3: Start gunicorn
echo "[3/3] Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-1}" \
    --timeout 180 \
    --preload \
    --access-logfile - \
    --error-logfile -
