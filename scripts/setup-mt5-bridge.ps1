# =============================================================================
# Dutchkem Trading AI — MT5 Bridge Setup Script (PowerShell / Windows)
# =============================================================================
# Sets up the SYNX-MT5-MCP bridge via Docker and Cloudflare Tunnel.
# Ports: REST API → 8082, WebSocket → 8081
# =============================================================================

$ErrorActionPreference = "Stop"

function Ok   { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail { param($msg) Write-Host "[FAIL] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "=== Dutchkem Trading AI — MT5 Bridge Setup ===" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check Docker ──────────────────────────────────────────────────────────
try {
    $dockerVer = docker --version 2>&1
    Ok "Docker installed: $dockerVer"
} catch {
    Fail "Docker is NOT installed."
    Write-Host "  Install: https://docs.docker.com/get-docker/"
    exit 1
}

# ── 2. Check Docker Compose ──────────────────────────────────────────────────
try {
    $composeVer = docker compose version 2>&1
    Ok "Docker Compose installed: $composeVer"
} catch {
    try {
        $composeVerV1 = docker-compose --version 2>&1
        Ok "Docker Compose (v1) installed: $composeVerV1"
    } catch {
        Fail "Docker Compose is NOT installed."
        Write-Host "  Install: https://docs.docker.com/compose/install/"
        exit 1
    }
}

# ── 3. Check cloudflared ─────────────────────────────────────────────────────
try {
    $cfVer = cloudflared --version 2>&1 | Select-Object -First 1
    Ok "cloudflared installed: $cfVer"
} catch {
    Warn "cloudflared is NOT installed (optional but recommended for tunnels)."
    Write-Host "  Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    Write-Host "  Without it, you must expose ports 8081/8082 publicly."
}

# ── 4. Create directory structure ─────────────────────────────────────────────
$BridgeDir = Join-Path (Get-Location) "mt5-bridge"
if (-not (Test-Path $BridgeDir)) {
    New-Item -ItemType Directory -Path $BridgeDir -Force | Out-Null
}
Ok "Bridge directory: $BridgeDir"

# ── 5. Create docker-compose.yml ─────────────────────────────────────────────
$composeContent = @'
version: "3.9"

services:
  mt5-bridge:
    image: ghcr.io/synx-ai/synx-mt5-mcp:latest
    container_name: mt5-bridge
    restart: unless-stopped
    ports:
      - "8082:8082"   # REST API
      - "8081:8081"   # WebSocket
    environment:
      - MT5_HOST=${MT5_HOST:-host.docker.internal}
      - MT5_PORT=${MT5_MT5_PORT:-1929}
      - MT5_LOGIN=${MT5_LOGIN:-}
      - MT5_PASSWORD=${MT5_PASSWORD:-}
      - MT5_SERVER=${MT5_SERVER:-}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - mt5-data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: mt5-cloudflared
    restart: unless-stopped
    command: tunnel --no-autoupdate run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    depends_on:
      mt5-bridge:
        condition: service_healthy

volumes:
  mt5-data:
'@

Set-Content -Path (Join-Path $BridgeDir "docker-compose.yml") -Value $composeContent -Encoding UTF8
Ok "Created docker-compose.yml"

# ── 6. Create .env template ──────────────────────────────────────────────────
$envContent = @'
# =============================================================================
# MT5 Bridge Environment Variables
# =============================================================================
# Copy this file and fill in your values.

# --- MetaTrader 5 Credentials ---------------------------------------------------
# IP/port where MT5 terminal is running (use host.docker.internal from Docker)
MT5_HOST=host.docker.internal
MT5_MT5_PORT=1929

# Your MT5 account credentials
MT5_LOGIN=
MT5_PASSWORD=
MT5_SERVER=

# --- Cloudflare Tunnel (optional — exposes bridge publicly) --------------------
# Generate at: https://one.dash.cloudflare.com → Networks → Tunnels
CLOUDFLARE_TUNNEL_TOKEN=
'@

Set-Content -Path (Join-Path $BridgeDir ".env") -Value $envContent -Encoding UTF8
Ok "Created .env template"

# ── 7. Print instructions ────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  NEXT STEPS" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Edit the .env file with your MT5 credentials:"
Write-Host "       $BridgeDir\.env"
Write-Host ""
Write-Host "  2. Ensure MetaTrader 5 is running on your machine with:"
Write-Host "       - 'Allow algo trading' enabled"
Write-Host "       - The MT5 API port configured (default: 1929)"
Write-Host ""
Write-Host "  3. Start the bridge:"
Write-Host "       cd $BridgeDir && docker compose up -d"
Write-Host ""
Write-Host "  4. (Optional) Create a Cloudflare Tunnel for public access:"
Write-Host "       cloudflared tunnel create dutchkem-mt5"
Write-Host "       cloudflared tunnel route dns dutchkem-mt5 mt5.yourdomain.com"
Write-Host "       Then add the tunnel token to $BridgeDir\.env"
Write-Host ""
Write-Host "  5. Test the bridge:"
Write-Host "       curl http://localhost:8082/health"
Write-Host ""
Write-Host "  6. Update your Django production env with the bridge URL:"
Write-Host "       MT5_HOST=mt5.yourdomain.com"
Write-Host "       MT5_PORT=443"
Write-Host "       MT5_WS_PORT=443"
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
