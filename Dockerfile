FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    TRADING_ENGINE=v6.5 \
    V65_ENABLED=true \
    WEB_CONCURRENCY=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# CRITICAL: Install setuptools<84 FIRST (84+ removed pkg_resources needed by drf-yasg)
RUN pip install --no-cache-dir "setuptools>=70.0.0,<84"

# Install Python deps
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    ; pip uninstall -y nvidia-nccl-cu12 2>/dev/null || true

# Verify pkg_resources is available (will fail build if not)
RUN python -c "from pkg_resources import DistributionNotFound; print('pkg_resources OK')"

# Create logs directory
RUN mkdir -p /app/logs

# Copy app
COPY backend/ ./backend/
COPY manage.py ./
COPY start.py ./start.py

EXPOSE 8000

# Python entrypoint — zero shell issues, zero CRLF risk
CMD ["python", "start.py"]
