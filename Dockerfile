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

# Install Python deps (setuptools for pkg_resources in drf-yasg)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    ; pip uninstall -y nvidia-nccl-cu12 2>/dev/null || true

# Create logs directory
RUN mkdir -p /app/logs

# Copy app
COPY backend/ ./backend/
COPY manage.py ./
COPY start.py ./start.py

EXPOSE 8000

# Python entrypoint — zero shell issues, zero CRLF risk
CMD ["python", "start.py"]
