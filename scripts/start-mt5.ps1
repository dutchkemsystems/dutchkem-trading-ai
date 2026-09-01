# =============================================================================
# Dutchkem Trading AI — Start MT5 Bridge (PowerShell)
# =============================================================================
# Starts only the MT5 Bridge container (standalone or within full stack).
#
# Prerequisites:
#   - MetaTrader 5 running on host with "Allow WebRequest" enabled
#   - MT5 API port set (default: 1929)
#   - Docker Desktop running
#
# Usage:
#   .\scripts\start-mt5.ps1                    # Standalone bridge
#   .\scripts\start-mt5.ps1 -WithTunnel        # Also start Cloudflare Tunnel
# =============================================================================

param(
    [switch]$WithTunnel
)

$ErrorActionPreference = "Stop"

function Ok   { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail { param($msg) Write-Host "[FAIL] $msg" -ForegroundColor Red }
function Step { param($msg) Write-Host "[..]   $msg" -ForegroundColor Cyan }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Dutchkem Trading AI — Starting MT5 Bridge" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check prerequisites ──────────────────────────────────────────────────
Step "Checking prerequisites..."

try { docker --version | Out-Null; Ok "Docker installed" }
catch { Fail "Docker is NOT installed."; exit 1 }

try { docker compose version | Out-Null; Ok "Docker Compose installed" }
catch { Fail "Docker Compose is NOT installed."; exit 1 }

# ── 2. Ensure bridge .env exists ─────────────────────────────────────────────
$bridgeDir = "mt5-bridge"
if (-not (Test-Path "$bridgeDir\.env")) {
    Warn "mt5-bridge/.env not found — creating template"
    $envContent = @"
# MT5 Bridge Environment Variables
MT5_HOST=host.docker.internal
MT5_MT5_PORT=1929
MT5_LOGIN=
MT5_PASSWORD=
MT5_SERVER=
CLOUDFLARE_TUNNEL_TOKEN=
"@
    Set-Content -Path "$bridgeDir\.env" -Value $envContent -Encoding UTF8
    Ok "Created mt5-bridge/.env — fill in your MT5 credentials"
}

# ── 3. Check for MT5 credentials ────────────────────────────────────────────
$envContent = Get-Content "$bridgeDir\.env" -Raw
if ($envContent -match "MT5_LOGIN=\s*$" -or $envContent -match "MT5_LOGIN=\s*\n") {
    Warn "MT5_LOGIN is empty in mt5-bridge/.env"
    Warn "MT5 Bridge may not connect to your terminal without credentials"
}

# ── 4. Start MT5 Bridge ──────────────────────────────────────────────────────
Step "Starting MT5 Bridge container..."

$profileArg = if ($WithTunnel) { @("--profile", "tunnel") } else { @() }

Push-Location $bridgeDir
& docker compose @profileArg up -d
Pop-Location

if ($LASTEXITCODE -eq 0) {
    Ok "MT5 Bridge started"
} else {
    Fail "MT5 Bridge failed to start"
    exit 1
}

# ── 5. Wait for health check ─────────────────────────────────────────────────
Step "Waiting for MT5 Bridge to become healthy..."
Start-Sleep -Seconds 5

$healthy = $false
for ($i = 0; $i -lt 6; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8082/health" -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 5
}

if ($healthy) {
    Ok "MT5 Bridge is healthy"
} else {
    Warn "MT5 Bridge health check timed out"
    Warn "Ensure MetaTrader 5 is running with algo trading enabled"
}

# ── 6. Print summary ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  MT5 Bridge Running" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  REST API:   http://localhost:8082" -ForegroundColor White
Write-Host "  WebSocket:  ws://localhost:8081" -ForegroundColor White
Write-Host "  Health:     http://localhost:8082/health" -ForegroundColor White
Write-Host ""
Write-Host "  Test connection:" -ForegroundColor Yellow
Write-Host "    curl http://localhost:8082/health" -ForegroundColor Yellow
Write-Host "    curl -X POST http://localhost:8082/connect -H 'Content-Type: application/json' -d '{}'" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Stop:       .\scripts\stop-mt5.ps1" -ForegroundColor Yellow
Write-Host ""
