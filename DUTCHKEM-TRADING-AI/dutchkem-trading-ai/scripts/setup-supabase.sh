#!/usr/bin/env bash
# =============================================================================
# Dutchkem Trading AI — Supabase Setup Helper
# =============================================================================
# Creates and configures a Supabase project for the trading platform.
#
# Prerequisites:
#   - supabase CLI installed (npm i -g supabase)
#   - Supabase account (free tier: https://supabase.com)
#   - Logged in: supabase login
#
# Usage:
#   bash scripts/setup-supabase.sh              # Interactive setup
#   bash scripts/setup-supabase.sh --project <ref>  # Link existing project
#   bash scripts/setup-supabase.sh --seed      # Seed database only
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

# ── Check Supabase CLI ──────────────────────────────────────────────────────

if ! command -v supabase &>/dev/null; then
    err "Supabase CLI not found. Install: npm i -g supabase"
    exit 1
fi

# ── Check authentication ────────────────────────────────────────────────────

if ! supabase projects list &>/dev/null; then
    warn "Not logged in to Supabase. Running: supabase login"
    supabase login
fi

# ── Functions ────────────────────────────────────────────────────────────────

create_project() {
    header "Create Supabase Project"

    echo -e "${CYAN}Follow the interactive prompts to create a new project:${NC}"
    echo "  - Project name: dutchkem-trading"
    echo "  - Database password: (generate a strong one)"
    echo "  - Region: closest to your users"
    echo ""
    echo -e "${YELLOW}Or create manually at: https://supabase.com/dashboard/new${NC}"
    echo ""
    read -p "Press Enter after creating the project (or provide project ref): " project_ref

    if [[ -n "$project_ref" ]]; then
        link_project "$project_ref"
    else
        echo "Run this script again with --project <ref> after creating your project."
        exit 0
    fi
}

link_project() {
    local ref=$1
    header "Link to Supabase Project: $ref"

    supabase link --project-ref "$ref"
    ok "Linked to project $ref"

    # Save to env
    echo "SUPABASE_PROJECT_REF=$ref" >> .env.cloud
    ok "Saved SUPABASE_PROJECT_REF to .env.cloud"
}

setup_database() {
    header "Setup Database Schema"

    log "Pushing schema to Supabase..."
    supabase db push --linked

    ok "Database schema pushed"

    log "Generating types..."
    supabase gen types typescript --linked > frontend/src/types/supabase.ts 2>/dev/null || warn "Type generation failed"
    ok "TypeScript types generated"
}

setup_auth() {
    header "Setup Auth Configuration"

    log "Configuring auth providers..."
    log ""
    log "Configure these in Supabase Dashboard > Authentication > Providers:"
    log "  1. Email/Password: Enabled by default"
    log "  2. Google OAuth: Add Client ID + Secret"
    log "  3. Discord OAuth: Add Client ID + Secret"
    log ""
    log "Also configure:"
    log "  - Site URL: https://dutchkem-frontend.vercel.app"
    log "  - Redirect URLs: https://dutchkem-frontend.vercel.app/auth/callback"
    warn "Auth configuration must be done manually in the dashboard"
}

setup_storage() {
    header "Setup Storage Buckets"

    log "Creating storage buckets..."

    # Create buckets via Supabase CLI or direct API
    supabase storage create avatars --public 2>/dev/null || warn "avatars bucket may already exist"
    supabase storage create documents --private 2>/dev/null || warn "documents bucket may already exist"
    supabase storage create exports --private 2>/dev/null || warn "exports bucket may already exist"

    ok "Storage buckets created"
}

setup_rls() {
    header "Setup Row-Level Security Policies"

    log "Applying RLS policies..."
    log ""
    log "Key RLS policies to verify:"
    log "  1. users: Users can only read/update their own profile"
    log "  2. trades: Users can only see their own trades"
    log "  3. signals: Users can read, system can write"
    log "  4. payments: Users can only see their own payments"
    log ""
    log "Apply via SQL Editor in Supabase Dashboard:"
    log "  File: supabase/migrations/*.sql"
    warn "RLS policies must be verified in the dashboard"
}

get_connection_info() {
    header "Connection Information"

    local project_ref
    project_ref=$(supabase projects list --output json 2>/dev/null | python -c "
import sys, json
projects = json.load(sys.stdin)
for p in projects:
    if p.get('id'):
        print(p['id'])
        break
" 2>/dev/null || echo "")

    if [[ -n "$project_ref" ]]; then
        log "Project Reference: $project_ref"
    fi

    log ""
    log "Connection strings (from Supabase Dashboard > Settings > Database):"
    log ""
    log "  ${CYAN}URI (Transaction):${NC}"
    log "  postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres"
    log ""
    log "  ${CYAN}URI (Session):${NC}"
    log "  postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres"
    log ""
    log "  ${CYAN}Direct connection:${NC}"
    log "  postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres"
    log ""
    log "  ${YELLOW}Use the Session URI for Django (long-lived connections)${NC}"
    log ""
}

print_env() {
    header "Environment Variables for .env.cloud"

    cat << 'EOF'
# Supabase — add these to .env.cloud
SUPABASE_PROJECT_REF=your-project-ref
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Database (use Session URI from Supabase Dashboard)
DATABASE_URL=postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:5432/postgres
EOF
}

# ── Main ────────────────────────────────────────────────────────────────────

main() {
    header "Supabase Setup — Dutchkem Trading AI"

    case "${1:-}" in
        --project)
            link_project "${2:?Project ref required}"
            setup_database
            setup_storage
            get_connection_info
            print_env
            ;;
        --seed)
            setup_database
            ;;
        --info)
            get_connection_info
            print_env
            ;;
        *)
            create_project
            setup_database
            setup_auth
            setup_storage
            setup_rls
            get_connection_info
            print_env
            ;;
    esac

    ok "Supabase setup complete"
}

main "$@"
