# =============================================================================
# Dutchkem Trading AI — Start Local Services (PowerShell)
# =============================================================================
# Starts PostgreSQL, Redis, MT5 Bridge, Django, Celery Worker, Celery Beat
# using Docker Compose full stack.
#
# Usage:
#   .\scripts\start-local.ps1
#   .\scripts\start-local.ps1 -SkipMT5        # Skip MT5 bridge
#   .\scripts\start-local.ps1 -Detached        # Run in background
# =============================================================================

param(
    [switch]$SkipMT5,
    [switch]$Detached
)

$ErrorActionPreference = "Stop"

function Ok   { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail { param($msg) Write-Host "[FAIL] $msg" -ForegroundColor Red }
function Step { param($msg) Write-Host "[..]   $msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Dutchkem Trading AI — Starting Local Services" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check prerequisites ──────────────────────────────────────────────────
Step "Checking prerequisites..."

try { docker --version | Out-Null; Ok "Docker installed" }
catch { Fail "Docker is NOT installed. Install: https://docs.docker.com/get-docker/"; exit 1 }

try { docker compose version | Out-Null; Ok "Docker Compose installed" }
catch { Fail "Docker Compose is NOT installed."; exit 1 }

# ── 2. Ensure .env exists ────────────────────────────────────────────────────
if (-not (Test-Path ".env")) {
    Warn ".env not found — copying from .env.example"
    Copy-Item ".env.example" ".env"
    Ok "Created .env from .env.example"
}

# ── 3. Set compose file ──────────────────────────────────────────────────────
$composeFile = "docker-compose.yml"
if (-not (Test-Path $composeFile)) {
    Fail "$composeFile not found. Run from project root."
    exit 1
}

# ── 4. Build images if needed ────────────────────────────────────────────────
Step "Building Docker images..."
docker compose -f $composeFile build --quiet
Ok "Images built"

# ── 5. Start services ────────────────────────────────────────────────────────
Step "Starting core services (db, redis, django, celery-worker, celery-beat)..."

$coreServices = @("db", "redis", "django", "celery-worker", "celery-beat")
$coreArgs = @("compose", "-f", $composeFile, "up", "-d") + $coreServices

if ($Detached) {
    & docker @coreArgs
} else {
    & docker @coreArgs
}

if ($LASTEXITCODE -eq 0) {
    Ok "Core services started"
} else {
    Fail "Failed to start core services"
    exit 1
}

# ── 6. Start MT5 Bridge (optional) ───────────────────────────────────────────
if (-not $SkipMT5) {
    Step "Starting MT5 Bridge..."
    & docker compose -f $composeFile up -d mt5-bridge
    if ($LASTEXITCODE -eq 0) {
        Ok "MT5 Bridge started"
    } else {
        Warn "MT5 Bridge failed to start (MT5 terminal may not be running)"
    }
}

# ── 7. Wait for health checks ────────────────────────────────────────────────
Step "Waiting for services to become healthy..."
Start-Sleep -Seconds 10

# Check Django health
$djangoHealthy = $false
for ($i = 0; $i -lt 6; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health/" -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $djangoHealthy = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 5
}

if ($djangoHealthy) {
    Ok "Django is healthy"
} else {
    Warn "Django health check timed out (may still be starting)"
}

# ── 8. Check MT5 Bridge ──────────────────────────────────────────────────────
if (-not $SkipMT5) {
    try {
        $mt5Response = Invoke-WebRequest -Uri "http://localhost:8082/health" -TimeoutSec 5 -ErrorAction Stop
        Ok "MT5 Bridge is healthy"
    } catch {
        Warn "MT5 Bridge health check failed (MT5 terminal may not be connected)"
    }
}

# ── 9. Print summary ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  All Services Started!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Service URLs:" -ForegroundColor White
Write-Host "    Django API:     http://localhost:8000/api/v1/" -ForegroundColor White
Write-Host "    Django Admin:   http://localhost:8000/admin/" -ForegroundColor White
Write-Host "    Swagger:        http://localhost:8000/swagger/" -ForegroundColor White
Write-Host "    Health Check:   http://localhost:8000/health/" -ForegroundColor White
Write-Host "    MT5 Bridge:     http://localhost:8082/health" -ForegroundColor White
Write-Host ""
Write-Host "  Docker commands:" -ForegroundColor Yellow
Write-Host "    View logs:      docker compose -f $composeFile logs -f" -ForegroundColor Yellow
Write-Host "    Stop all:       .\scripts\stop-local.ps1" -ForegroundColor Yellow
Write-Host "    Restart:        .\scripts\stop-local.ps1; .\scripts\start-local.ps1" -ForegroundColor Yellow
Write-Host ""
