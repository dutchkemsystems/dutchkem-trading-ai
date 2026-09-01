# =============================================================================
# Dutchkem Trading AI — Quick Start Script (PowerShell / Windows)
# =============================================================================
# Checks environment, installs deps, runs migrations, creates superuser,
# and starts the Django development server.
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Dutchkem Trading AI — Quick Start ===" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check Python version ──────────────────────────────────────────────────
Write-Host "[1/6] Checking Python version..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.(\d+)") {
        $minor = [int]$Matches[1]
        if ($minor -lt 10) {
            Write-Host "  Python 3.10+ required. Found: $pythonVersion" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "  OK: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  Python is NOT installed or not in PATH." -ForegroundColor Red
    Write-Host "  Install from: https://www.python.org/downloads/"
    exit 1
}

# ── 2. Create virtual environment ────────────────────────────────────────────
Write-Host "[2/6] Setting up virtual environment..." -ForegroundColor Yellow

$venvPath = Join-Path (Get-Location) ".venv"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
    Write-Host "  Created .venv" -ForegroundColor Green
} else {
    Write-Host "  .venv already exists" -ForegroundColor Green
}

# Activate
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
& $activateScript

# ── 3. Install requirements ──────────────────────────────────────────────────
Write-Host "[3/6] Installing requirements..." -ForegroundColor Yellow

$requirementsPath = Join-Path (Get-Location) "backend\requirements.txt"
if (Test-Path $requirementsPath) {
    pip install -r $requirementsPath --quiet
    Write-Host "  Requirements installed" -ForegroundColor Green
} else {
    Write-Host "  backend\requirements.txt not found" -ForegroundColor Red
    exit 1
}

# ── 4. Run migrations ────────────────────────────────────────────────────────
Write-Host "[4/6] Running migrations..." -ForegroundColor Yellow

Set-Location (Join-Path (Get-Location) "backend")
python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Migrations failed" -ForegroundColor Red
    exit 1
}
Write-Host "  Migrations applied" -ForegroundColor Green

# ── 5. Create superuser (interactive) ────────────────────────────────────────
Write-Host "[5/6] Creating superuser..." -ForegroundColor Yellow
Write-Host "  (Press Ctrl+C to skip if you already have one)" -ForegroundColor Gray
Write-Host ""

python manage.py createsuperuser

# ── 6. Start server ──────────────────────────────────────────────────────────
Write-Host "[6/6] Starting Django server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Django is running at:" -ForegroundColor Cyan
Write-Host "    API:         http://127.0.0.1:8000/api/v1/" -ForegroundColor White
Write-Host "    Admin:       http://127.0.0.1:8000/admin/" -ForegroundColor White
Write-Host "    Swagger:     http://127.0.0.1:8000/swagger/" -ForegroundColor White
Write-Host "    ReDoc:       http://127.0.0.1:8000/redoc/" -ForegroundColor White
Write-Host "    Health:      http://127.0.0.1:8000/health/" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press Ctrl+C to stop the server." -ForegroundColor Gray
Write-Host ""

python manage.py runserver
