#!/bin/bash
# ============================================
# Fly.io Frontend Deployment Script
# Deploys Dutchkem Trading AI frontend to Fly.io
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Dutchkem Trading AI - Frontend Deploy  ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ============================================
# Step 1: Check prerequisites
# ============================================
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check for flyctl
if ! command -v flyctl &> /dev/null; then
    if ! command -v fly &> /dev/null; then
        echo -e "${RED}Fly.io CLI (flyctl) is not installed.${NC}"
        echo "Install it from: https://fly.io/docs/hands-on/install-flyctl/"
        exit 1
    fi
    FLY_CMD="fly"
else
    FLY_CMD="flyctl"
fi
echo -e "${GREEN}✓ Fly.io CLI is installed${NC}"

# Check if logged in
if ! $FLY_CMD auth whoami &> /dev/null; then
    echo "Logging in to Fly.io..."
    $FLY_CMD auth login
fi
echo -e "${GREEN}✓ Logged in to Fly.io${NC}"

# ============================================
# Step 2: Create app (if needed)
# ============================================
echo ""
echo -e "${YELLOW}Step 2: Creating Fly.io app...${NC}"

# Check if app exists
if ! $FLY_CMD apps list | grep -q "dutchkem-trading-ai-frontend"; then
    echo "Creating new app: dutchkem-trading-ai-frontend"
    $FLY_CMD apps create dutchkem-trading-ai-frontend --org personal
else
    echo -e "${GREEN}✓ App already exists${NC}"
fi

# ============================================
# Step 3: Set Environment Variables
# ============================================
echo ""
echo -e "${YELLOW}Step 3: Setting environment variables...${NC}"

# Create fly.toml for frontend
cat > fly.frontend.toml << 'EOF'
app = "dutchkem-trading-ai-frontend"
primary_region = "ams"

[build]
  dockerfile = "dutchkem-trading-ai/frontend/Dockerfile.fly"

[http_service]
  internal_port = 80
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true

[[vm]]
  memory = "256mb"
  cpu_kind = "shared"
  cpus = 1
EOF

echo -e "${GREEN}✓ fly.frontend.toml created${NC}"

# ============================================
# Step 4: Deploy
# ============================================
echo ""
echo -e "${YELLOW}Step 4: Deploying frontend to Fly.io...${NC}"

$FLY_CMD deploy \
    --config fly.frontend.toml \
    --app dutchkem-trading-ai-frontend \
    --copy-config

echo -e "${GREEN}✓ Frontend deployed${NC}"

# ============================================
# Step 5: Verify Deployment
# ============================================
echo ""
echo -e "${YELLOW}Step 5: Verifying deployment...${NC}"

$FLY_CMD status --app dutchkem-trading-ai-frontend

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Frontend Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Frontend URL:${NC} https://dutchkem-trading-ai-frontend.fly.dev"
echo ""
echo -e "${YELLOW}Post-Deployment Steps:${NC}"
echo "1. Update backend CORS settings to allow frontend domain:"
echo "   $FLY_CMD secrets set CORS_ALLOWED_ORIGINS='https://dutchkem-trading-ai-frontend.fly.dev' --app dutchkem-trading-ai"
echo ""
echo "2. Update backend CSRF trusted origins:"
echo "   $FLY_CMD secrets set CSRF_TRUSTED_ORIGINS='https://dutchkem-trading-ai-frontend.fly.dev' --app dutchkem-trading-ai"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs:    $FLY_CMD logs --app dutchkem-trading-ai-frontend"
echo "  Status:       $FLY_CMD status --app dutchkem-trading-ai-frontend"
echo "  Redeploy:     $FLY_CMD deploy --config fly.frontend.toml --app dutchkem-trading-ai-frontend"
echo ""
