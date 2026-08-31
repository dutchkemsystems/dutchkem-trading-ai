# ============================================
# Dutchkem Trading AI 2.0 — Fly.io Deployment Script
# Run after `fly auth login` succeeds
# ============================================
# Run this from: C:\DUTCHKEM-TRADING-AI

Write-Output "=========================================="
Write-Output "Dutchkem Trading AI 2.0 — Fly.io Deploy"
Write-Output "=========================================="
Write-Output ""

$ErrorActionPreference = "Stop"

# Refresh PATH to include fly
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# ---- STEP 1: Verify Auth ----
Write-Output "[1/10] Verifying Fly.io authentication..."
$auth = fly auth whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Not authenticated! Run 'fly auth login' first."
    exit 1
}
Write-Output "  Authenticated as: $auth"
Write-Output ""

# ---- STEP 2: Generate Django Secret Key ----
Write-Output "[2/10] Generating Django secret key..."
$DJANGO_SECRET = python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to generate Django secret key"
    exit 1
}
Write-Output "  Secret key generated."
Write-Output ""

# ---- STEP 3: Create Apps ----
Write-Output "[3/10] Creating Fly.io apps..."
fly apps create dutchkem-trading-ai --org personal 2>&1 | Out-Null
Write-Output "  Backend app: dutchkem-trading-ai"
fly apps create dutchkem-trading-ai-frontend --org personal 2>&1 | Out-Null
Write-Output "  Frontend app: dutchkem-trading-ai-frontend"
Write-Output ""

# ---- STEP 4: Create PostgreSQL Database ----
Write-Output "[4/10] Creating PostgreSQL database..."
fly postgres create --name dutchkem-db --region ams --org personal 2>&1
Write-Output ""

# ---- STEP 5: Attach Database ----
Write-Output "[5/10] Attaching PostgreSQL to backend..."
$attachOutput = fly postgres attach dutchkem-db --app dutchkem-trading-ai 2>&1
Write-Output $attachOutput
# Extract DATABASE_URL from output
$dbUrlLine = ($attachOutput | Select-String "DATABASE_URL").ToString()
Write-Output "  Database attached."
Write-Output ""

# ---- STEP 6: Set Secrets ----
Write-Output "[6/10] Setting environment secrets..."
fly secrets set DJANGO_SECRET_KEY="$DJANGO_SECRET" --app dutchkem-trading-ai
fly secrets set DJANGO_SETTINGS_MODULE="config.settings_production" --app dutchkem-trading-ai
fly secrets set ALLOWED_HOSTS="dutchkem-trading-ai.fly.dev,dutchkem-trading-ai.up.railway.app" --app dutchkem-trading-ai
fly secrets set CORS_ALLOWED_ORIGINS="https://dutchkem-trading-ai-frontend.fly.dev" --app dutchkem-trading-ai
fly secrets set CSRF_TRUSTED_ORIGINS="https://dutchkem-trading-ai-frontend.fly.dev" --app dutchkem-trading-ai
fly secrets set SECURE_SSL_REDIRECT="True" --app dutchkem-trading-ai
fly secrets set SESSION_COOKIE_SECURE="True" --app dutchkem-trading-ai
fly secrets set CSRF_COOKIE_SECURE="True" --app dutchkem-trading-ai
Write-Output "  Secrets configured."
Write-Output ""

# ---- STEP 7: Deploy Backend ----
Write-Output "[7/10] Deploying backend to Fly.io..."
Write-Output "  (This may take several minutes...)"
fly deploy --app dutchkem-trading-ai
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backend deployment failed!"
    exit 1
}
Write-Output "  Backend deployed successfully!"
Write-Output ""

# ---- STEP 8: Run Migrations ----
Write-Output "[8/10] Running database migrations..."
fly ssh console --app dutchkem-trading-ai -C "python manage.py migrate --no-input"
Write-Output "  Migrations complete."
Write-Output ""

# ---- STEP 9: Collect Static Files ----
Write-Output "[9/10] Collecting static files..."
fly ssh console --app dutchkem-trading-ai -C "python manage.py collectstatic --no-input"
Write-Output "  Static files collected."
Write-Output ""

# ---- STEP 10: Create Superuser ----
Write-Output "[10/10] Creating admin superuser..."
fly ssh console --app dutchkem-trading-ai -C "python manage.py shell -c \""from accounts.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@dutchkem.com', 'Dutchkem2024!', first_name='Admin', last_name='User'); print('Admin user ready')\""
Write-Output "  Superuser created."
Write-Output ""

# ---- Deploy Frontend ----
Write-Output "Deploying frontend to Fly.io..."
Write-Output "  (This may take a few minutes...)"
fly deploy --config fly.frontend.toml --app dutchkem-trading-ai-frontend
if ($LASTEXITCODE -ne 0) {
    Write-Error "Frontend deployment failed!"
    exit 1
}
Write-Output "  Frontend deployed successfully!"
Write-Output ""

# ---- FINAL: Status Check ----
Write-Output "=========================================="
Write-Output "DEPLOYMENT COMPLETE"
Write-Output "=========================================="
Write-Output ""
Write-Output "Backend:  https://dutchkem-trading-ai.fly.dev"
Write-Output "Frontend: https://dutchkem-trading-ai-frontend.fly.dev"
Write-Output "API:      https://dutchkem-trading-ai.fly.dev/api/v1/"
Write-Output "Swagger:  https://dutchkem-trading-ai.fly.dev/swagger/"
Write-Output "Admin:    https://dutchkem-trading-ai.fly.dev/admin/"
Write-Output "Health:   https://dutchkem-trading-ai.fly.dev/health/"
Write-Output ""
Write-Output "Admin Login: admin / Dutchkem2024!"
Write-Output ""
Write-Output "Backend Status:"
fly status --app dutchkem-trading-ai
Write-Output ""
Write-Output "Frontend Status:"
fly status --app dutchkem-trading-ai-frontend
