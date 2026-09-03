FROM python:3.12-slim
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
# STEP 1: Install setuptools FIRST
RUN pip install --upgrade pip setuptools wheel
# STEP 2: Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# STEP 3: Copy application
COPY . .
# STEP 4: Run migrations and collectstatic
RUN python manage.py migrate --no-input || echo "Migration skipped"
RUN python manage.py collectstatic --no-input || echo "Collectstatic skipped"
# STEP 5: Start Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "config.wsgi:application", "--workers", "2", "--timeout", "120"]
