#!/bin/bash
set -euo pipefail

# =============================================================================
# Dutchkem Trading AI — MT5 Bridge Setup Script (Bash / Linux / macOS)
# =============================================================================
# Sets up the SYNX-MT5-MCP bridge via Docker and Cloudflare Tunnel.
# Ports: REST API → 8082, WebSocket → 8081
# =============================================================================

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }

echo -e "${BOLD}=== Dutchkem Trading AI — MT5 Bridge Setup ===${NC}"
echo ""

# ── 1. Check Docker ──────────────────────────────────────────────────────────
if command -v docker &> /dev/null; then
    ok "Docker installed: $(docker --version)"
else
    fail "Docker is NOT installed."
    echo "  Install: https://docs.docker.com/get-docker/"
    exit 1
fi

# ── 2. Check Docker Compose ──────────────────────────────────────────────────
if docker compose version &> /dev/null; then
    ok "Docker Compose installed: $(docker compose version --short)"
elif command -v docker-compose &> /dev/null; then
    ok "Docker Compose (v1) installed: $(docker-compose --version)"
else
    fail "Docker Compose is NOT installed."
    echo "  Install: https://docs.docker.com/compose/install/"
    exit 1
fi

# ── 3. Check cloudflared ─────────────────────────────────────────────────────
if command -v cloudflared &> /dev/null; then
    ok "cloudflared installed: $(cloudflared --version 2>&1 | head -1)"
else
    warn "cloudflared is NOT installed (optional but recommended for tunnels)."
    echo "  Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    echo "  Without it, you must expose ports 8081/8082 publicly."
fi

# ── 4. Create directory structure ─────────────────────────────────────────────
BRIDGE_DIR="$(pwd)/mt5-bridge"
mkdir -p "$BRIDGE_DIR"
ok "Bridge directory: $BRIDGE_DIR"

# ── 5. Create docker-compose.yml ─────────────────────────────────────────────
cat > "$BRIDGE_DIR/docker-compose.yml" <<'YAML'
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
YAML
ok "Created docker-compose.yml"

# ── 6. Create .env template ──────────────────────────────────────────────────
cat > "$BRIDGE_DIR/.env" <<'ENV'
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
ENV
ok "Created .env template"

# ── 7. Print instructions ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  NEXT STEPS${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  1. Edit the .env file with your MT5 credentials:"
echo "       $BRIDGE_DIR/.env"
echo ""
echo "  2. Ensure MetaTrader 5 is running on your machine with:"
echo "       - 'Allow algo trading' enabled"
echo "       - The MT5 API port configured (default: 1929)"
echo ""
echo "  3. Start the bridge:"
echo "       cd $BRIDGE_DIR && docker compose up -d"
echo ""
echo "  4. (Optional) Create a Cloudflare Tunnel for public access:"
echo "       cloudflared tunnel create dutchkem-mt5"
echo "       cloudflared tunnel route dns dutchkem-mt5 mt5.yourdomain.com"
echo "       Then add the tunnel token to $BRIDGE_DIR/.env"
echo ""
echo "  5. Test the bridge:"
echo "       curl http://localhost:8082/health"
echo ""
echo "  6. Update your Django production env with the bridge URL:"
echo "       MT5_HOST=mt5.yourdomain.com"
echo "       MT5_PORT=443"
echo "       MT5_WS_PORT=443"
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
