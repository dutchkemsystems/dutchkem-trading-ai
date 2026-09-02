FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    TRADING_ENGINE=v6.5 \
    V65_ENABLED=true \
    WEB_CONCURRENCY=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps — minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps, then remove CUDA/GPU packages not needed on Render CPU
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    ; pip uninstall -y nvidia-nccl-cu12 2>/dev/null || true

# Copy app
COPY backend/ ./backend/
COPY manage.py ./

EXPOSE 8000

# Simple shell command — Render sets PORT env var
CMD sh -c "python manage.py migrate --no-input && python manage.py collectstatic --no-input && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 180 --preload"
