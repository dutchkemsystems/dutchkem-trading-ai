#!/bin/bash
# ============================================
# MT5 Bridge Setup Script
# Quick setup for SYNX-MT5-MCP with Cloudflare Tunnel
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MT5 Bridge Setup - Dutchkem Trading AI${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MT5_DIR="$PROJECT_DIR/mcp-servers/synx-mt5"

# ============================================
# Step 1: Check if cloudflared is installed
# ============================================
echo -e "${YELLOW}Step 1: Checking cloudflared...${NC}"

if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}cloudflared not found. Installing...${NC}"

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
            sudo dpkg -i /tmp/cloudflared.deb
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install cloudflared
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo -e "${YELLOW}For Windows, please download cloudflared from:${NC}"
        echo "https://github.com/cloudflare/cloudflared/releases/latest"
        echo ""
        echo "Add it to your PATH and re-run this script."
        exit 1
    fi

    echo -e "${GREEN}✓ cloudflared installed${NC}"
else
    echo -e "${GREEN}✓ cloudflared already installed${NC}"
fi

# ============================================
# Step 2: Create .env file
# ============================================
echo ""
echo -e "${YELLOW}Step 2: Creating .env file...${NC}"

if [ ! -f "$MT5_DIR/.env" ]; then
    cat > "$MT5_DIR/.env" << 'EOF'
# Cloudflare Tunnel Token
# Get this from: Zero Trust → Networks → Tunnels → Configure → Token
CF_TUNNEL_TOKEN=your_token_here

# MT5 Configuration
MT5_HOST=host.docker.internal
MT5_PORT=3000
EOF
    echo -e "${GREEN}✓ .env file created${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# ============================================
# Step 3: Start Docker Compose
# ============================================
echo ""
echo -e "${YELLOW}Step 3: Starting MT5 bridge services...${NC}"

cd "$MT5_DIR"

if command -v docker &> /dev/null; then
    docker compose -f docker-compose.mt5.yml up -d
    echo -e "${GREEN}✓ Services started${NC}"

    # Wait for healthy status
    echo "Waiting for services to be healthy..."
    sleep 5

    # Check status
    docker compose -f docker-compose.mt5.yml ps
else
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# ============================================
# Step 4: Print Instructions
# ============================================
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Get your Cloudflare Tunnel token:"
echo "   - Go to: https://one.dash.cloudflare.com/"
echo "   - Navigate: Networks → Tunnels"
echo "   - Click 'Configure' on your tunnel"
echo "   - Copy the token"
echo ""
echo "2. Add token to .env file:"
echo "   Edit: $MT5_DIR/.env"
echo "   Set: CF_TUNNEL_TOKEN=your_actual_token"
echo ""
echo "3. Restart services:"
echo "   cd $MT5_DIR"
echo "   docker compose -f docker-compose.mt5.yml restart"
echo ""
echo "4. Update your Fly.io backend:"
echo "   fly secrets set MT5_MCP_URL=https://mt5-bridge.your-domain.com --app dutchkem-trading-ai"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs:    docker compose -f docker-compose.mt5.yml logs -f"
echo "  Stop:         docker compose -f docker-compose.mt5.yml down"
echo "  Restart:      docker compose -f docker-compose.mt5.yml restart"
echo "  Status:       docker compose -f docker-compose.mt5.yml ps"
echo ""
