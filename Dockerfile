FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    TRADING_ENGINE=v6.5 \
    V65_ENABLED=true

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY manage.py ./

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --no-input && python manage.py collectstatic --no-input && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4 --timeout 120"]
