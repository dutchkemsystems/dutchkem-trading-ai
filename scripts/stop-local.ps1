# =============================================================================
# Dutchkem Trading AI — Stop Local Services (PowerShell)
# =============================================================================
# Stops all Docker Compose services gracefully.
#
# Usage:
#   .\scripts\stop-local.ps1
#   .\scripts\stop-local.ps1 -IncludeMT5     # Also stop MT5 bridge
#   .\scripts\stop-local.ps1 -Volumes        # Also remove data volumes (DESTRUCTIVE)
# =============================================================================

param(
    [switch]$IncludeMT5,
    [switch]$Volumes
)

$ErrorActionPreference = "Stop"

function Ok   { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail { param($msg) Write-Host "[FAIL] $msg" -ForegroundColor Red }
function Step { param($msg) Write-Host "[..]   $msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Dutchkem Trading AI — Stopping Local Services" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$composeFile = "docker-compose.yml"
if (-not (Test-Path $composeFile)) {
    Fail "$composeFile not found. Run from project root."
    exit 1
}

# ── 1. Stop core services ────────────────────────────────────────────────────
Step "Stopping core services (django, celery-worker, celery-beat, redis, db)..."

$stopArgs = @("compose", "-f", $composeFile, "down")
if ($Volumes) {
    $stopArgs += "-v"
    Warn "Data volumes will be REMOVED (PostgreSQL data, Redis data)"
}

& docker @stopArgs

if ($LASTEXITCODE -eq 0) {
    Ok "Core services stopped"
} else {
    Warn "Some services may not have stopped cleanly"
}

# ── 2. Stop MT5 Bridge (optional) ────────────────────────────────────────────
if ($IncludeMT5) {
    Step "Stopping MT5 Bridge..."
    $mt5Args = @("compose", "-f", $composeFile, "down")
    if ($Volumes) {
        $mt5Args += "-v"
    }
    & docker @mt5Args mt5-bridge
    if ($LASTEXITCODE -eq 0) {
        Ok "MT5 Bridge stopped"
    } else {
        Warn "MT5 Bridge may not have stopped cleanly"
    }
}

# ── 3. Also stop standalone mt5-bridge if running ─────────────────────────────
$mt5BridgeRunning = docker ps --format "{{.Names}}" 2>$null | Select-String "dutchkem-mt5-bridge"
if ($mt5BridgeRunning) {
    Step "Stopping standalone MT5 bridge container..."
    docker stop dutchkem-mt5-bridge 2>$null
    Ok "Standalone MT5 bridge stopped"
}

# ── 4. Print summary ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  All Services Stopped" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  To restart:    .\scripts\start-local.ps1" -ForegroundColor Yellow
Write-Host "  To view:       docker ps" -ForegroundColor Yellow
Write-Host ""
