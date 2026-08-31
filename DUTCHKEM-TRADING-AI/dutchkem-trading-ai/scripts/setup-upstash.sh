#!/usr/bin/env bash
# =============================================================================
# Dutchkem Trading AI — Upstash Redis Setup Helper
# =============================================================================
# Creates and configures an Upstash Redis instance for:
#   - Celery broker (async task queue)
#   - Django cache (session + trading data)
#   - Django Channels (WebSocket layer)
#
# Prerequisites:
#   - Upstash account (free tier: https://upstash.com)
#   - curl installed
#
# Usage:
#   bash scripts/setup-upstash.sh              # Interactive setup
#   bash scripts/setup-upstash.sh --url <url> --token <token>  # Configure directly
# =============================================================================

set -euo pipefail

# ── Colors ───────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log()    { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"; }
ok()     { echo -e "${GREEN}[$(date +%H:%M:%S)] ✓${NC} $1"; }
warn()   { echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠${NC} $1"; }
err()    { echo -e "${RED}[$(date +%H:%M:%S)] ✗${NC} $1"; }
header() { echo -e "\n${CYAN}══════════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}\n"; }

# ── Upstash API helper ──────────────────────────────────────────────────────

upstash_api() {
    local method=$1
    local endpoint=$2
    local data=${3:-}

    if [[ -z "${UPSTASH_API_TOKEN:-}" ]]; then
        err "UPSTASH_API_TOKEN not set"
        return 1
    fi

    local response
    if [[ "$method" == "GET" ]]; then
        response=$(curl -s -H "Authorization: Bearer $UPSTASH_API_TOKEN" \
            "https://api.upstash.com/v1$endpoint")
    else
        response=$(curl -s -X POST \
            -H "Authorization: Bearer $UPSTASH_API_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "https://api.upstash.com/v1$endpoint")
    fi

    echo "$response"
}

# ── Create Redis instance ───────────────────────────────────────────────────

create_redis() {
    header "Create Upstash Redis Instance"

    echo -e "${CYAN}Follow these steps:${NC}"
    echo ""
    echo "  1. Go to: ${GREEN}https://console.upstash.com${NC}"
    echo "  2. Click 'Create Database'"
    echo "  3. Choose:"
    echo "     - Type: Redis"
    echo "     - Name: dutchkem-redis"
    echo "     - Region: Closest to your users"
    echo "     - Plan: Free (10K commands/day)"
    echo "  4. Click 'Create'"
    echo ""
    echo -e "${YELLOW}After creating, copy the REST URL and Token:${NC}"
    echo ""

    read -p "UPSTASH_REDIS_REST_URL: " upstash_url
    read -s -p "UPSTASH_REDIS_REST_TOKEN: " upstash_token
    echo ""

    if [[ -n "$upstash_url" && -n "$upstash_token" ]]; then
        configure_redis "$upstash_url" "$upstash_token"
    else
        err "URL and token are required"
        exit 1
    fi
}

configure_redis() {
    local url=$1
    local token=$2

    header "Configure Redis"

    # Test connection
    log "Testing Redis connection..."
    local test_result
    test_result=$(curl -s -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d '["PING"]' \
        "$url" 2>/dev/null || echo "")

    if [[ "$test_result" == *'"PONG"'* ]]; then
        ok "Redis connection successful"
    else
        warn "Could not verify connection (may still work)"
    fi

    # Save to .env.cloud
    log "Saving to .env.cloud..."
    cat >> .env.cloud << EOF

# Upstash Redis — Dutchkem Trading AI
UPSTASH_REDIS_REST_URL=$url
UPSTASH_REDIS_REST_TOKEN=$token
REDIS_URL=$url
CELERY_BROKER_URL=$url
EOF

    ok "Configuration saved to .env.cloud"

    # Configure Redis settings
    log "Configuring Redis settings..."
    configure_redis_settings "$url" "$token"
}

configure_redis_settings() {
    local url=$1
    local token=$2

    # Set maxmemory policy
    log "Setting maxmemory-policy to allkeys-lru..."
    curl -s -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d '["CONFIG","SET","maxmemory-policy","allkeys-lru"]' \
        "$url" > /dev/null 2>&1 || warn "Could not set maxmemory-policy"

    # Set maxmemory (Upstash free tier limit)
    log "Setting maxmemory to 256mb..."
    curl -s -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d '["CONFIG","SET","maxmemory","268435456"]' \
        "$url" > /dev/null 2>&1 || warn "Could not set maxmemory"

    ok "Redis settings configured"
}

# ── Verify configuration ────────────────────────────────────────────────────

verify_config() {
    header "Verify Redis Configuration"

    local url=${1:-${UPSTASH_REDIS_REST_URL:-}}
    local token=${2:-${UPSTASH_REDIS_REST_TOKEN:-}}

    if [[ -z "$url" || -z "$token" ]]; then
        warn "No credentials to verify"
        return
    fi

    # Test PING
    log "Testing PING..."
    local ping_result
    ping_result=$(curl -s -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d '["PING"]' \
        "$url" 2>/dev/null)

    if [[ "$ping_result" == *'"PONG"'* ]]; then
        ok "PING: PONG"
    else
        err "PING failed: $ping_result"
        return 1
    fi

    # Test SET/GET
    log "Testing SET/GET..."
    local test_key="dutchkem:health:$(date +%s)"
    curl -s -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "[\"SET\",\"$test_key\",\"ok\",\"EX\",\"60\"]" \
        "$url" > /dev/null 2>&1

    local get_result
    get_result=$(curl -s -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "[\"GET\",\"$test_key\"]" \
        "$url" 2>/dev/null)

    if [[ "$get_result" == *'"ok"'* ]]; then
        ok "SET/GET: working"
    else
        warn "SET/GET test inconclusive"
    fi

    # Cleanup
    curl -s -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d "[\"DEL\",\"$test_key\"]" \
        "$url" > /dev/null 2>&1

    # Get info
    log "Redis info:"
    local info_result
    info_result=$(curl -s -X POST \
        -H "Authorization: Bearer $token" \
        -H "Content-Type: application/json" \
        -d '["INFO","server"]' \
        "$url" 2>/dev/null)

    if [[ -n "$info_result" ]]; then
        echo "$info_result" | head -5
    fi
}

# ── Render integration ──────────────────────────────────────────────────────

setup_render_env() {
    header "Set Redis URL in Render"

    local url=${1:-${UPSTASH_REDIS_REST_URL:-}}
    local token=${2:-${UPSTASH_REDIS_REST_TOKEN:-}}

    if [[ -z "$url" || -z "$token" ]]; then
        warn "No Redis credentials available"
        return
    fi

    if command -v render &>/dev/null; then
        log "Setting REDIS_URL in Render services..."

        # Set for API service
        render env set REDIS_URL="$url" --service dutchkem-api 2>/dev/null || warn "Could not set REDIS_URL for dutchkem-api"

        # Set for worker
        render env set REDIS_URL="$url" --service dutchkem-celery-worker 2>/dev/null || warn "Could not set REDIS_URL for dutchkem-celery-worker"

        # Set for beat
        render env set REDIS_URL="$url" --service dutchkem-celery-beat 2>/dev/null || warn "Could not set REDIS_URL for dutchkem-celery-beat"

        ok "REDIS_URL set in Render services"
    else
        warn "Render CLI not found — set REDIS_URL manually in Render dashboard"
        echo ""
        echo "  Go to: https://dashboard.render.com"
        echo "  Select each service → Environment → Add REDIS_URL=$url"
    fi
}

# ── Print environment variables ─────────────────────────────────────────────

print_env() {
    header "Environment Variables"

    cat << 'EOF'
# Upstash Redis — add these to .env.cloud
UPSTASH_REDIS_REST_URL=https://your-instance.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token

# Django / Celery / Channels (same URL)
REDIS_URL=https://your-instance.upstash.io
CELERY_BROKER_URL=https://your-instance.upstash.io

# Render Dashboard — set these env vars:
#   REDIS_URL = https://your-instance.upstash.io
#   CELERY_BROKER_URL = https://your-instance.upstash.io
EOF
}

# ── Show usage guide ────────────────────────────────────────────────────────

usage_guide() {
    header "Upstash Free Tier — Usage Guide"

    echo -e "${CYAN}Upstash Free Tier Limits:${NC}"
    echo "  - Max commands: 10,000/day"
    echo "  - Max connections: 20"
    echo "  - Max data: 256 MB"
    echo "  - Max key size: 512 KB"
    echo ""
    echo -e "${YELLOW}Dutchkem Usage Breakdown:${NC}"
    echo "  - Celery broker:  ~5,000 commands/day (task dispatch + results)"
    echo "  - Django cache:   ~3,000 commands/day (session + trading)"
    echo "  - Channel layers: ~1,000 commands/day (WebSocket)"
    echo "  - Overhead:       ~1,000 commands/day"
    echo ""
    echo -e "${GREEN}Tips to stay within free tier:${NC}"
    echo "  1. Increase CELERY_RESULT_EXPIRES to reduce result storage"
    echo "  2. Use LocMemCache as fallback for non-critical caching"
    echo "  3. Monitor usage: https://console.upstash.com → Usage"
    echo ""
}

# ── Main ────────────────────────────────────────────────────────────────────

main() {
    header "Upstash Redis Setup — Dutchkem Trading AI"

    case "${1:-}" in
        --url)
            local url=${2:?URL required}
            local token=${3:?Token required}
            configure_redis "$url" "$token"
            verify_config "$url" "$token"
            setup_render_env "$url" "$token"
            print_env
            ;;
        --verify)
            verify_config
            ;;
        --render)
            setup_render_env
            ;;
        --info)
            print_env
            usage_guide
            ;;
        *)
            create_redis
            verify_config
            setup_render_env
            print_env
            usage_guide
            ;;
    esac

    ok "Upstash setup complete"
}

main "$@"
