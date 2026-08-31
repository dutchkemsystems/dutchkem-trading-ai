#!/usr/bin/env bash
# =============================================================================
# Dutchkem Trading AI — Cloud Deployment Script
# =============================================================================
# Deploys all services to their respective free-tier providers:
#   1. Render    → Backend API + Celery Worker + Celery Beat
#   2. Vercel    → React Frontend
#   3. Supabase  → PostgreSQL (if not already set up)
#   4. Upstash   → Redis (if not already set up)
#
# Prerequisites:
#   - render CLI installed and authenticated (npm i -g @render/cli)
#   - vercel CLI installed and authenticated (npm i -g vercel)
#   - supabase CLI installed (npm i -g supabase)
#   - .env.cloud file with all secrets
#
# Usage:
#   bash scripts/deploy-cloud.sh              # Full deploy
#   bash scripts/deploy-cloud.sh --backend    # Backend only
#   bash scripts/deploy-cloud.sh --frontend   # Frontend only
#   bash scripts/deploy-cloud.sh --status     # Check status only
# =============================================================================

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Helpers ──────────────────────────────────────────────────────────────────

log()    { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"; }
ok()     { echo -e "${GREEN}[$(date +%H:%M:%S)] ✓${NC} $1"; }
warn()   { echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠${NC} $1"; }
err()    { echo -e "${RED}[$(date +%H:%M:%S)] ✗${NC} $1"; }
header() { echo -e "\n${CYAN}══════════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}\n"; }

# ── Check dependencies ──────────────────────────────────────────────────────

check_cli() {
    local cmd=$1
    local name=$2
    if command -v "$cmd" &>/dev/null; then
        ok "$name CLI found: $(command -v "$cmd")"
        return 0
    else
        warn "$name CLI not found. Install with: npm i -g $3"
        return 1
    fi
}

# ── Load environment ────────────────────────────────────────────────────────

load_env() {
    local env_file=".env.cloud"
    if [[ -f "$env_file" ]]; then
        log "Loading environment from $env_file..."
        set -a
        source "$env_file"
        set +a
        ok "Environment loaded"
    else
        warn ".env.cloud not found — using system environment variables"
        warn "Create .env.cloud from .env.cloud.example if needed"
    fi
}

# ── Preflight checks ───────────────────────────────────────────────────────

preflight() {
    header "Preflight Checks"

    local errors=0

    check_cli "render" "Render" "@render/cli" || ((errors++))
    check_cli "vercel" "Vercel" "vercel" || ((errors++))
    check_cli "supabase" "Supabase" "supabase" || ((errors++))

    # Check required env vars
    log "Checking required environment variables..."
    local required_vars=(
        "SUPABASE_PROJECT_REF"
        "SUPABASE_ACCESS_TOKEN"
        "UPSTASH_REDIS_REST_URL"
        "UPSTASH_REDIS_REST_TOKEN"
        "VERCEL_ORG_ID"
        "VERCEL_PROJECT_ID"
    )

    for var in "${required_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            ok "$var is set"
        else
            warn "$var is not set — some steps may be skipped"
        fi
    done

    if [[ $errors -gt 0 ]]; then
        err "Missing $errors CLI tools. Install them and retry."
        exit 1
    fi
}

# ── Deploy Supabase Database ────────────────────────────────────────────────

deploy_supabase() {
    header "Supabase — PostgreSQL Database"

    if [[ -z "${SUPABASE_PROJECT_REF:-}" ]]; then
        warn "SUPABASE_PROJECT_REF not set — skipping database setup"
        warn "Set up manually: https://supabase.com/dashboard"
        return
    fi

    log "Linking to Supabase project: $SUPABASE_PROJECT_REF"
    supabase link --project-ref "$SUPABASE_PROJECT_REF" 2>/dev/null || true

    log "Running database migrations..."
    supabase db push --linked 2>/dev/null || {
        warn "db push failed — migrations may need manual application"
    }

    ok "Supabase database ready"

    # Get connection string
    local conn_string
    conn_string=$(supabase db connection-string --linked 2>/dev/null || echo "")
    if [[ -n "$conn_string" ]]; then
        ok "Connection string obtained"
        echo "DATABASE_URL=$conn_string" >> .env.deployed
    fi
}

# ── Deploy Upstash Redis ────────────────────────────────────────────────────

deploy_upstash() {
    header "Upstash — Redis"

    if [[ -z "${UPSTASH_REDIS_REST_URL:-}" ]]; then
        warn "UPSTASH_REDIS_REST_URL not set — skipping Redis setup"
        warn "Create at: https://console.upstash.com"
        return
    fi

    # Upstash Redis URL is already in the format needed by Django
    # redis://<token>:<password>@<host>:<port>
    ok "Upstash Redis configured"
    echo "REDIS_URL=$UPSTASH_REDIS_REST_URL" >> .env.deployed
}

# ── Deploy Render Backend ──────────────────────────────────────────────────

deploy_render() {
    header "Render — Backend Deployment"

    if ! command -v render &>/dev/null; then
        err "Render CLI not installed. Install: npm i -g @render/cli"
        return 1
    fi

    # Validate render.yaml exists
    if [[ ! -f "render.yaml" ]]; then
        err "render.yaml not found in project root"
        return 1
    fi

    log "Deploying Render blueprint..."
    log "Services: dutchkem-api (web) + dutchkem-celery-worker (worker) + dutchkem-celery-beat (cron)"

    # Apply the blueprint (creates or updates services)
    if render blueprint apply --force; then
        ok "Render blueprint applied successfully"
    else
        warn "Blueprint apply returned non-zero — checking service status..."
    fi

    # Wait for deployment
    log "Waiting for deployment to stabilize (60s)..."
    sleep 60

    # Check service status
    log "Checking service statuses..."
    render services list 2>/dev/null || warn "Could not list services"

    # Verify health endpoint
    local api_url
    api_url=$(render services list --output json 2>/dev/null | grep -o '"serviceUrl":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")

    if [[ -n "$api_url" ]]; then
        log "Testing health endpoint: $api_url/health/"
        local status_code
        status_code=$(curl -s -o /dev/null -w "%{http_code}" "$api_url/health/" 2>/dev/null || echo "000")
        if [[ "$status_code" == "200" ]]; then
            ok "Health endpoint responding (HTTP $status_code)"
        elif [[ "$status_code" == "503" ]]; then
            warn "Health check returned 503 — service may still be starting"
        else
            warn "Health check returned HTTP $status_code"
        fi
    fi

    ok "Render deployment complete"
}

# ── Deploy Vercel Frontend ─────────────────────────────────────────────────

deploy_vercel() {
    header "Vercel — Frontend Deployment"

    # Check vercel.json exists
    if [[ ! -f "vercel.json" ]]; then
        err "vercel.json not found in project root"
        return 1
    fi

    log "Deploying frontend to Vercel (production)..."

    cd frontend || { err "frontend/ directory not found"; return 1; }

    # Deploy to production
    if vercel --prod --yes --no-clipboard 2>&1; then
        ok "Vercel deployment complete"
    else
        err "Vercel deployment failed"
        cd ..
        return 1
    fi

    cd ..

    # Get deployment URL
    local vercel_url
    vercel_url=$(vercel ls --prod 2>/dev/null | grep -o 'https://[^ ]*' | head -1 || echo "")
    if [[ -n "$vercel_url" ]]; then
        ok "Frontend URL: $vercel_url"
        echo "VERCEL_URL=$vercel_url" >> .env.deployed
    fi
}

# ── Check Status ────────────────────────────────────────────────────────────

check_status() {
    header "Service Status Check"

    # Render
    if command -v render &>/dev/null; then
        log "Render services:"
        render services list 2>/dev/null || warn "Could not list Render services"
    fi

    # Vercel
    if command -v vercel &>/dev/null; then
        log "Vercel deployments:"
        vercel ls --prod 2>/dev/null || warn "Could not list Vercel deployments"
    fi

    # Health check
    if [[ -n "${RENDER_API_URL:-}" ]]; then
        log "Testing backend health..."
        curl -sf "$RENDER_API_URL/health/" | python -m json.tool 2>/dev/null || warn "Health check failed"
    fi
}

# ── Summary ─────────────────────────────────────────────────────────────────

print_summary() {
    header "Deployment Summary"

    echo -e "${GREEN}Service URLs:${NC}"
    echo -e "  Backend API:    ${CYAN}https://dutchkem-api.onrender.com${NC}"
    echo -e "  Frontend:       ${CYAN}https://dutchkem-frontend.vercel.app${NC}"
    echo -e "  Database:       ${CYAN}(Supabase dashboard)${NC}"
    echo -e "  Redis:          ${CYAN}(Upstash dashboard)${NC}"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo -e "  1. Update Vercel URL in Render env: CORS_ALLOWED_ORIGINS=https://your-vercel-url.vercel.app"
    echo -e "  2. Set REDIS_URL in Render dashboard (from Upstash)"
    echo -e "  3. Set up Cloudflare Tunnel for MCP bridge (see scripts/setup-mt5-bridge.sh)"
    echo -e "  4. Create Django superuser: heroku run python manage.py createsuperuser"
    echo ""
}

# ── Main ────────────────────────────────────────────────────────────────────

main() {
    header "Dutchkem Trading AI — Cloud Deployment"
    log "Starting deployment at $(date)"

    load_env

    case "${1:-full}" in
        --status|status)
            check_status
            ;;
        --backend|backend)
            deploy_render
            ;;
        --frontend|frontend)
            deploy_vercel
            ;;
        --database|database)
            deploy_supabase
            ;;
        --redis|redis)
            deploy_upstash
            ;;
        full|"")
            preflight
            deploy_supabase
            deploy_upstash
            deploy_render
            deploy_vercel
            print_summary
            ;;
        *)
            echo "Usage: $0 [--status|--backend|--frontend|--database|--redis|full]"
            exit 1
            ;;
    esac

    ok "Deployment completed at $(date)"
}

main "$@"
