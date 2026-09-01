Write-Host "=== Deploying to Railway ===" -ForegroundColor Green

# Check railway CLI
$railway = Get-Command railway -ErrorAction SilentlyContinue
if (-not $railway) {
    Write-Host "Installing Railway CLI..." -ForegroundColor Yellow
    npm install -g @railway/cli
}

# Login
railway login 2>&1

# Create project
railway project create dutchkem-trading-ai 2>&1

# Link project
railway link 2>&1

# Add PostgreSQL
railway add --name dutchkem-db --type postgresql 2>&1

# Add Redis
railway add --name dutchkem-redis --type redis 2>&1

# Set environment variables
railway variables set DJANGO_SETTINGS_MODULE="config.settings_production" 2>&1
railway variables set ALLOWED_HOSTS="dutchkem-trading-ai.up.railway.app" 2>&1
railway variables set CORS_ALLOWED_ORIGINS="https://dutchkem-trading-ai-frontend.up.railway.app" 2>&1
railway variables set SECURE_SSL_REDIRECT="True" 2>&1
railway variables set SESSION_COOKIE_SECURE="True" 2>&1
railway variables set CSRF_COOKIE_SECURE="True" 2>&1

# Deploy
railway up 2>&1

Write-Host "=== Backend Deployed ===" -ForegroundColor Green
Write-Host "URL: https://dutchkem-trading-ai.up.railway.app" -ForegroundColor Cyan
