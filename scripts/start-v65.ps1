# =============================================================================
# Dutchkem Trading AI — V6.5 Full Stack Startup Script
# =============================================================================
# Starts all services: Docker (PostgreSQL, Redis, MT5 Bridge, Django, Celery),
# populates Celery beat schedule, initializes symbols, shows status.
#
# Usage:
#   powershell -File scripts/start-v65.ps1
#   powershell -File scripts/start-v65.ps1 -SkipMigrations
# =============================================================================

param(
    [switch]$SkipMigrations,
    [switch]$SkipSymbols,
    [switch]$SkipSchedule,
    [switch]$Build
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Dutchkem Trading AI — V6.5 Startup" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check Docker ─────────────────────────────────────────────────────
Write-Host "[1/7] Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker not found" }
    Write-Host "  OK: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Docker is not installed or not in PATH." -ForegroundColor Red
    Write-Host "  Install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor Red
    exit 1
}

# ── Step 2: Check .env file ──────────────────────────────────────────────────
Write-Host "[2/7] Checking .env configuration..." -ForegroundColor Yellow
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envFile)) {
    $envExample = Join-Path $ProjectRoot ".env.example"
    if (Test-Path $envExample) {
        Write-Host "  .env not found. Copying from .env.example..." -ForegroundColor Yellow
        Copy-Item $envExample $envFile
        Write-Host "  Created .env from .env.example — edit it with your credentials." -ForegroundColor Yellow
    } else {
        Write-Host "  ERROR: No .env or .env.example found." -ForegroundColor Red
        exit 1
    }
}
Write-Host "  OK: .env found" -ForegroundColor Green

# ── Step 3: Start Docker Compose ─────────────────────────────────────────────
Write-Host "[3/7] Starting Docker Compose stack..." -ForegroundColor Yellow
$composeFile = Join-Path $ProjectRoot "docker-compose.full.yml"
if (-not (Test-Path $composeFile)) {
    Write-Host "  ERROR: docker-compose.full.yml not found." -ForegroundColor Red
    exit 1
}

$buildArg = @()
if ($Build) { $buildArg = @("--build") }

Push-Location $ProjectRoot
docker compose -f docker-compose.full.yml up -d @buildArg
$composeExit = $LASTEXITCODE
Pop-Location

if ($composeExit -ne 0) {
    Write-Host "  ERROR: Docker Compose failed to start." -ForegroundColor Red
    exit 1
}
Write-Host "  OK: Docker Compose started" -ForegroundColor Green

# ── Step 4: Wait for health checks ───────────────────────────────────────────
Write-Host "[4/7] Waiting for services to be healthy (up to 60s)..." -ForegroundColor Yellow
$maxWait = 60
$elapsed = 0
$allHealthy = $false

while ($elapsed -lt $maxWait -and -not $allHealthy) {
    Start-Sleep -Seconds 5
    $elapsed += 5
    
    $containers = docker ps --format "{{.Names}}\t{{.Status}}" 2>&1
    $healthy = ($containers | Select-String "healthy").Count
    $total = ($containers | Select-String "dutchkem").Count
    
    Write-Host "  [$elapsed/${maxWait}s] $healthy/$total containers healthy" -ForegroundColor Gray
    
    if ($healthy -ge 3) {  # At least db, redis, django
        $allHealthy = $true
    }
}

if (-not $allHealthy) {
    Write-Host "  WARNING: Some services may not be fully healthy yet." -ForegroundColor Yellow
}

# ── Step 5: Run migrations ──────────────────────────────────────────────────
if (-not $SkipMigrations) {
    Write-Host "[5/7] Running database migrations..." -ForegroundColor Yellow
    docker compose -f docker-compose.full.yml exec -T django python manage.py migrate --noinput 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: Migrations applied" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Migrations may have issues — check logs." -ForegroundColor Yellow
    }
} else {
    Write-Host "[5/7] Skipping migrations (--SkipMigrations)" -ForegroundColor Gray
}

# ── Step 6: Populate Celery beat schedule ────────────────────────────────────
if (-not $SkipSchedule) {
    Write-Host "[6/7] Populating Celery beat schedule..." -ForegroundColor Yellow
    $populateScript = @"
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_production')
django.setup()
from django_celery_beat.models import PeriodicTask, CrontabSchedule
# Default trading schedule
crons = [
    ('*/5 * * * *', 'Market data ingestion'),
    ('*/15 * * * *', 'Signal generation cycle'),
    ('0 * * * *', 'Hourly risk assessment'),
    ('0 0 * * *', 'Daily performance report'),
    ('*/1 * * * *', 'V6.5 trading pipeline cycle'),
]
for expr, name in crons:
    parts = expr.split()
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute=parts[0], hour=parts[1],
        day_of_month=parts[2], month_of_year=parts[3], day_of_week=parts[4]
    )
    if not PeriodicTask.objects.filter(name=name).exists():
        PeriodicTask.objects.create(
            name=name, task='config.celery.debug_task',
            crontab=schedule, enabled=True
        )
        print(f'  Created: {name} ({expr})')
    else:
        print(f'  Exists:  {name}')
print('Schedule populated.')
"@
    docker compose -f docker-compose.full.yml exec -T django python -c $populateScript 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: Celery schedule populated" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Schedule population had issues — check logs." -ForegroundColor Yellow
    }
} else {
    Write-Host "[6/7] Skipping schedule (--SkipSchedule)" -ForegroundColor Gray
}

# ── Step 7: Initialize symbols ──────────────────────────────────────────────
if (-not $SkipSymbols) {
    Write-Host "[7/7] Initializing trading symbols..." -ForegroundColor Yellow
    $symbolScript = @"
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_production')
django.setup()
from risk_management.models import TradingSettings
settings, created = TradingSettings.objects.get_or_create(id=1)
symbols = 'EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,NZDUSD,EURGBP,EURJPY,GBPJPY,AUDJPY,EURAUD,EURCHF,GBPCAD,USDTRY,USDZAR,USDMXN,USDCNH,XAUUSD,XAGUSD,XAUEUR,BTCUSD,ETHUSD,SOLUSD,US30,US500,NAS100,GER40'
if not settings.active_symbols or settings.active_symbols != symbols:
    settings.active_symbols = symbols
    settings.save()
    print(f'  Initialized {len(symbols.split(\",\"))} symbols')
else:
    print(f'  Already configured: {len(settings.active_symbols.split(\",\"))} symbols')
"@
    docker compose -f docker-compose.full.yml exec -T django python -c $symbolScript 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: Symbols initialized" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Symbol init had issues — check logs." -ForegroundColor Yellow
    }
} else {
    Write-Host "[7/7] Skipping symbols (--SkipSymbols)" -ForegroundColor Gray
}

# ── Show Status ──────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Service Status" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
docker compose -f docker-compose.full.yml ps
Write-Host ""

# ── Summary ──────────────────────────────────────────────────────────────────
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  V6.5 Stack is running!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Services:" -ForegroundColor White
Write-Host "    Django API:      http://localhost:8000" -ForegroundColor Gray
Write-Host "    PostgreSQL:      localhost:5432" -ForegroundColor Gray
Write-Host "    Redis:           localhost:6379" -ForegroundColor Gray
Write-Host "    MT5 Bridge REST: http://localhost:8082" -ForegroundColor Gray
Write-Host "    MT5 Bridge WS:   ws://localhost:8081" -ForegroundColor Gray
Write-Host ""
Write-Host "  Useful commands:" -ForegroundColor White
Write-Host "    docker compose -f docker-compose.full.yml logs -f django" -ForegroundColor Gray
Write-Host "    docker compose -f docker-compose.full.yml logs -f celery-worker" -ForegroundColor Gray
Write-Host "    docker compose -f docker-compose.full.yml down" -ForegroundColor Gray
Write-Host ""
