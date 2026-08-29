#!/bin/bash
# ============================================
# Fly.io Backend Deployment Script
# Deploys Dutchkem Trading AI backend to Fly.io
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Dutchkem Trading AI - Fly.io Deploy   ${NC}"
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
        echo ""
        echo "Windows (PowerShell):"
        echo "  iwr https://fly.io/install.ps1 -UseBasicParsing | iex"
        echo ""
        echo "macOS:"
        echo "  brew install flyctl"
        echo ""
        echo "Linux:"
        echo "  curl -L https://fly.io/install.sh | sh"
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
# Step 2: Generate Django Secret Key
# ============================================
echo ""
echo -e "${YELLOW}Step 2: Generating Django secret key...${NC}"

DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null || \
    python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null || \
    openssl rand -hex 32)

echo -e "${GREEN}✓ Secret key generated${NC}"

# ============================================
# Step 3: Set Fly.io Secrets
# ============================================
echo ""
echo -e "${YELLOW}Step 3: Setting Fly.io secrets...${NC}"

echo "Setting secrets (these will be encrypted and stored securely)..."

$FLY_CMD secrets set \
    DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
    ALLOWED_HOSTS="dutchkem-trading-ai.fly.dev,dutchkem-trading-ai-frontend.fly.dev" \
    CORS_ALLOWED_ORIGINS="https://dutchkem-trading-ai-frontend.fly.dev" \
    CSRF_TRUSTED_ORIGINS="https://dutchkem-trading-ai-frontend.fly.dev" \
    --app dutchkem-trading-ai

echo -e "${GREEN}✓ Basic secrets configured${NC}"

echo ""
echo -e "${YELLOW}⚠️  Please set the following secrets manually:${NC}"
echo "  $FLY_CMD secrets set DATABASE_URL='postgres://...' --app dutchkem-trading-ai"
echo "  $FLY_CMD secrets set REDIS_URL='redis://...' --app dutchkem-trading-ai"
echo "  $FLY_CMD secrets set MT5_MCP_URL='https://mt5-bridge.your-domain.com' --app dutchkem-trading-ai"
echo "  $FLY_CMD secrets set KORA_SECRET_KEY='...' --app dutchkem-trading-ai"
echo "  $FLY_CMD secrets set KORA_PUBLIC_KEY='...' --app dutchkem-trading-ai"
echo ""

read -p "Press Enter after setting the secrets above (or Ctrl+C to cancel)..."

# ============================================
# Step 4: Create Fly.io Postgres (Optional)
# ============================================
echo ""
echo -e "${YELLOW}Step 4: Database setup...${NC}"

read -p "Do you want to create a Fly.io Postgres database? (y/N): " CREATE_DB

if [[ "$CREATE_DB" =~ ^[Yy]$ ]]; then
    echo "Creating Fly.io Postgres database..."

    # Create the Postgres cluster
    $FLY_CMD postgres create \
        --name dutchkem-db \
        --region ams \
        --initial-cluster-size 1 \
        --vm-size shared-cpu-1x \
        --volume-size 1

    # Attach to the app
    $FLY_CMD postgres attach dutchkem-db --app dutchkem-trading-ai

    echo -e "${GREEN}✓ Postgres database created and attached${NC}"

    # Get the database URL
    DB_URL=$($FLY_CMD postgres connect -a dutchkem-db --echo --quiet 2>/dev/null | grep "DATABASE_URL" || true)
    if [ -n "$DB_URL" ]; then
        echo -e "${YELLOW}Database URL: $DB_URL${NC}"
    fi
else
    echo -e "${YELLOW}Skipping database creation. Make sure to set DATABASE_URL manually.${NC}"
fi

# ============================================
# Step 5: Create Redis (Optional)
# ============================================
echo ""
echo -e "${YELLOW}Step 5: Redis setup...${NC}"

read -p "Do you want to use Upstash Redis? (y/N): " CREATE_REDIS

if [[ "$CREATE_REDIS" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Please set up Upstash Redis:${NC}"
    echo "1. Go to https://console.upstash.com/"
    echo "2. Create a new Redis database in Amsterdam (AMS) region"
    echo "3. Copy the REDIS_URL"
    echo "4. Run: $FLY_CMD secrets set REDIS_URL='your_redis_url' --app dutchkem-trading-ai"
    echo ""
    read -p "Press Enter after setting the Redis URL..."
else
    echo -e "${YELLOW}Skipping Redis setup. Make sure to set REDIS_URL manually.${NC}"
fi

# ============================================
# Step 6: Launch/Deploy
# ============================================
echo ""
echo -e "${YELLOW}Step 6: Deploying to Fly.io...${NC}"

# Check if fly.toml exists
if [ ! -f "fly.toml" ]; then
    echo "No fly.toml found. Running fly launch..."
    $FLY_CMD launch --copy-config --yes
else
    echo "fly.toml found. Deploying..."
    $FLY_CMD deploy --copy-config
fi

echo -e "${GREEN}✓ Deployment initiated${NC}"

# ============================================
# Step 7: Run Migrations
# ============================================
echo ""
echo -e "${YELLOW}Step 7: Running database migrations...${NC}"

read -p "Do you want to run Django migrations now? (y/N): " RUN_MIGRATIONS

if [[ "$RUN_MIGRATIONS" =~ ^[Yy]$ ]]; then
    $FLY_CMD ssh console --app dutchkem-trading-ai -C "python manage.py migrate --noinput"
    echo -e "${GREEN}✓ Migrations completed${NC}"

    # Create superuser
    read -p "Do you want to create a superuser? (y/N): " CREATE_SUPERUSER
    if [[ "$CREATE_SUPERUSER" =~ ^[Yy]$ ]]; then
        $FLY_CMD ssh console --app dutchkem-trading-ai -C "python manage.py createsuperuser"
    fi
fi

# ============================================
# Step 8: Verify Deployment
# ============================================
echo ""
echo -e "${YELLOW}Step 8: Verifying deployment...${NC}"

echo "Checking deployment status..."
$FLY_CMD status --app dutchkem-trading-ai

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Backend URL:${NC} https://dutchkem-trading-ai.fly.dev"
echo -e "${GREEN}Admin Panel:${NC} https://dutchkem-trading-ai.fly.dev/admin/"
echo -e "${GREEN}API Docs:${NC}    https://dutchkem-trading-ai.fly.dev/api/docs/"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View logs:    $FLY_CMD logs --app dutchkem-trading-ai"
echo "  SSH:          $FLY_CMD ssh console --app dutchkem-trading-ai"
echo "  Status:       $FLY_CMD status --app dutchkem-trading-ai"
echo "  Redeploy:     $FLY_CMD deploy --app dutchkem-trading-ai"
echo "  Scale:        $FLY_CMD scale count 2 --app dutchkem-trading-ai"
echo ""
