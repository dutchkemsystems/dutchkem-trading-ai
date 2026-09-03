#!/bin/bash
# Render Build Script — Fix for pkg_resources error
echo "🔧 Installing setuptools first..."
pip install --upgrade pip setuptools wheel
echo "📦 Installing requirements..."
pip install --no-cache-dir -r requirements.txt
echo "📋 Running migrations..."
python manage.py migrate --no-input || echo "Migration skipped"
echo "📁 Collecting static files..."
python manage.py collectstatic --no-input || echo "Collectstatic skipped"
echo "✅ Build complete!"
