# =============================================================================
# Dutchkem Trading AI — Stop MT5 Bridge (PowerShell)
# =============================================================================
# Stops the MT5 Bridge container gracefully.
#
# Usage:
#   .\scripts\stop-mt5.ps1
#   .\scripts\stop-mt5.ps1 -Volumes     # Also remove MT5 data volume
# =============================================================================

param(
    [switch]$Volumes
)

$ErrorActionPreference = "Stop"

function Ok   { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Step { param($msg) Write-Host "[..]   $msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Dutchkem Trading AI — Stopping MT5 Bridge" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$bridgeDir = "mt5-bridge"

# ── 1. Stop standalone mt5-bridge container (if running from main compose) ────
$standaloneRunning = docker ps --format "{{.Names}}" 2>$null | Select-String "dutchkem-mt5-bridge"
if ($standaloneRunning) {
    Step "Stopping standalone MT5 bridge container..."
    docker stop dutchkem-mt5-bridge 2>$null
    docker rm dutchkem-mt5-bridge 2>$null
    Ok "Standalone MT5 bridge stopped"
}

# ── 2. Stop via mt5-bridge docker-compose ─────────────────────────────────────
if (Test-Path "$bridgeDir\docker-compose.yml") {
    Step "Stopping MT5 Bridge via docker-compose..."
    $stopArgs = @("compose", "-f", "$bridgeDir\docker-compose.yml", "down")
    if ($Volumes) {
        $stopArgs += "-v"
        Warn "MT5 data volume will be REMOVED"
    }

    Push-Location $bridgeDir
    & docker @stopArgs
    Pop-Location

    if ($LASTEXITCODE -eq 0) {
        Ok "MT5 Bridge stopped"
    } else {
        Warn "MT5 Bridge may not have stopped cleanly"
    }
}

# ── 3. Print summary ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  MT5 Bridge Stopped" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  To restart:    .\scripts\start-mt5.ps1" -ForegroundColor Yellow
Write-Host ""
