#!/bin/bash
# ============================================
# MT5 Bridge Setup Script
# Sets up SYNX-MT5-MCP with Cloudflare Tunnel
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Dutchkem Trading AI - MT5 Bridge Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ============================================
# Step 1: Check prerequisites
# ============================================
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    echo "  - Windows: https://docs.docker.com/desktop/install/windows-install/"
    echo "  - macOS: https://docs.docker.com/desktop/install/mac-install/"
    echo "  - Linux: https://docs.docker.com/engine/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check for Docker Compose
if ! docker compose version &> /dev/null; then
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Docker Compose is not installed.${NC}"
        exit 1
    fi
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi
echo -e "${GREEN}✓ Docker Compose is available${NC}"

# ============================================
# Step 2: Install cloudflared (if not present)
# ============================================
echo ""
echo -e "${YELLOW}Step 2: Installing cloudflared...${NC}"

if ! command -v cloudflared &> /dev/null; then
    echo "Installing cloudflared..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o /tmp/cloudflared.deb
            sudo dpkg -i /tmp/cloudflared.deb
        elif command -v yum &> /dev/null; then
            curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.rpm -o /tmp/cloudflared.rpm
            sudo rpm -i /tmp/cloudflared.rpm
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install cloudflared
        else
            echo -e "${RED}Please install Homebrew first: https://brew.sh${NC}"
            exit 1
        fi
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows (Git Bash / MSYS2)
        echo -e "${YELLOW}For Windows, please download cloudflared from:${NC}"
        echo "https://github.com/cloudflare/cloudflared/releases/latest"
        echo "Add it to your PATH after installation."
        exit 1
    fi

    echo -e "${GREEN}✓ cloudflared installed${NC}"
else
    echo -e "${GREEN}✓ cloudflared is already installed${NC}"
fi

# ============================================
# Step 3: Authenticate with Cloudflare
# ============================================
echo ""
echo -e "${YELLOW}Step 3: Authenticating with Cloudflare...${NC}"

if [ ! -f "$HOME/.cloudflared/cert.pem" ]; then
    echo "Opening browser for Cloudflare authentication..."
    echo -e "${YELLOW}Select the domain you want to use for the MT5 bridge.${NC}"
    cloudflared tunnel login
    echo -e "${GREEN}✓ Authentication successful${NC}"
else
    echo -e "${GREEN}✓ Already authenticated with Cloudflare${NC}"
fi

# ============================================
# Step 4: Create Tunnel
# ============================================
echo ""
echo -e "${YELLOW}Step 4: Creating Cloudflare Tunnel...${NC}"

TUNNEL_NAME="dutchkem-mt5-bridge"

# Check if tunnel already exists
if cloudflared tunnel list | grep -q "$TUNNEL_NAME"; then
    echo -e "${YELLOW}Tunnel '$TUNNEL_NAME' already exists. Using existing tunnel.${NC}"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
else
    echo "Creating new tunnel: $TUNNEL_NAME"
    cloudflared tunnel create "$TUNNEL_NAME"
    TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
fi
echo -e "${GREEN}✓ Tunnel created/available: $TUNNEL_ID${NC}"

# ============================================
# Step 5: Configure DNS Route
# ============================================
echo ""
echo -e "${YELLOW}Step 5: Configuring DNS route...${NC}"

read -p "Enter your domain (e.g., mt5-bridge.your-domain.com): " MT5_DOMAIN

if [ -z "$MT5_DOMAIN" ]; then
    MT5_DOMAIN="mt5-bridge.dutchkem.com"
    echo "Using default domain: $MT5_DOMAIN"
fi

# Route DNS to tunnel
cloudflared tunnel route dns "$TUNNEL_NAME" "$MT5_DOMAIN" 2>/dev/null || true
echo -e "${GREEN}✓ DNS configured: $MT5_DOMAIN → tunnel${NC}"

# ============================================
# Step 6: Create .env file for Docker Compose
# ============================================
echo ""
echo -e "${YELLOW}Step 6: Creating configuration files...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create .env file
cat > "$SCRIPT_DIR/.env" << EOF
# Cloudflare Tunnel Token
# Get this from: Zero Trust → Networks → Tunnels → Configure → Token
CF_TUNNEL_TOKEN=your_token_here

# MT5 Configuration
MT5_HOST=host.docker.internal
MT5_PORT=3000
EOF

echo -e "${YELLOW}⚠️  Please edit $SCRIPT_DIR/.env and add your CF_TUNNEL_TOKEN${NC}"
echo -e "${YELLOW}   Get it from: Zero Trust → Networks → Tunnels → Configure → Token${NC}"

# ============================================
# Step 7: Start Services
# ============================================
echo ""
echo -e "${YELLOW}Step 7: Starting MT5 Bridge services...${NC}"

cd "$SCRIPT_DIR"

echo "Starting services..."
$COMPOSE_CMD -f docker-compose.mt5.yml up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Check if services are running
if $COMPOSE_CMD -f docker-compose.mt5.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✓ Services are running${NC}"
else
    echo -e "${RED}⚠️  Services may not be running properly. Check logs:${NC}"
    echo "  $COMPOSE_CMD -f docker-compose.mt5.yml logs"
fi

# ============================================
# Step 8: Print Summary
# ============================================
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}MT5 Bridge URL:${NC} https://$MT5_DOMAIN"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Edit .env file with your Cloudflare Tunnel token"
echo "2. Ensure MT5 is running on your local machine"
echo "3. Update your Fly.io backend secrets:"
echo "   fly secrets set MT5_MCP_URL=https://$MT5_DOMAIN"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs:      $COMPOSE_CMD -f docker-compose.mt5.yml logs -f"
echo "  Stop services:  $COMPOSE_CMD -f docker-compose.mt5.yml down"
echo "  Restart:        $COMPOSE_CMD -f docker-compose.mt5.yml restart"
echo "  Status:         $COMPOSE_CMD -f docker-compose.mt5.yml ps"
echo ""
echo -e "${GREEN}Happy Trading! 🚀${NC}"
