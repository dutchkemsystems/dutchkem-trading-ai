# Dutchkem Trading AI — Cloud Deployment Guide (Free Tier)

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│                  │     │                      │     │                  │
│  Vercel (CDN)    │────▶│  Render (Backend)    │────▶│  Supabase        │
│  React Frontend  │     │  Django + Celery     │     │  PostgreSQL      │
│                  │     │                      │     │                  │
└─────────────────┘     └──────────┬───────────┘     └──────────────────┘
                                   │
                          ┌────────┴────────┐
                          │                  │
                          │  Upstash Redis   │
                          │  Cache + Broker  │
                          │                  │
                          └─────────────────┘
                                   │
                          ┌────────┴────────┐
                          │                  │
                          │  Cloudflare      │
                          │  Tunnel (MT5)    │
                          │                  │
                          └─────────────────┘
```

## Cost Summary

| Service   | Provider    | Plan    | Cost/Month |
|-----------|-------------|---------|------------|
| Frontend  | Vercel      | Free    | $0         |
| Backend   | Render      | Free    | $0         |
| Celery    | Render      | Free    | $0         |
| Database  | Supabase    | Free    | $0         |
| Redis     | Upstash     | Free    | $0         |
| MT5 Tunnel| Cloudflare  | Free    | $0         |
| **Total** |             |         | **$0**     |

**Free Tier Limits:**
- **Render**: Spins down after 15 min inactivity, 750 hrs/month
- **Supabase**: 500MB database, 1GB bandwidth, 50K MAU
- **Upstash**: 10K commands/day, 256MB storage
- **Vercel**: 100GB bandwidth, 100K edge requests
- **Cloudflare**: Unlimited tunnels on free plan

---

## Step 1: Supabase (PostgreSQL Database)

### 1.1 Create Project
1. Go to [supabase.com](https://supabase.com) and sign up
2. Click **New Project**
3. Configure:
   - **Organization**: Create new or use existing
   - **Project name**: `dutchkem-trading`
   - **Database password**: Generate a strong password (save it!)
   - **Region**: Choose closest to your users (e.g., `us-east-1`)
4. Click **Create new project**
5. Wait ~2 minutes for provisioning

### 1.2 Get Connection String
1. Go to **Settings** → **Database**
2. Scroll to **Connection string**
3. Select **URI** format
4. Copy the full URL:
   ```
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```

### 1.3 Run Migrations
```bash
cd backend

# Set the URL temporarily
export DATABASE_URL="postgresql://postgres.xxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 1.4 Verify
```bash
# Test connection
python manage.py dbshell
```

---

## Step 2: Upstash (Redis)

### 2.1 Create Instance
1. Go to [upstash.com](https://upstash.com) and sign up
2. Click **Create Database**
3. Configure:
   - **Name**: `dutchkem-redis`
   - **Region**: Choose same region as Render (e.g., `us-east-1`)
   - **Type**: Regional (free tier)
4. Click **Create**

### 2.2 Get Connection URL
1. Go to the database details page
2. Copy the **Redis URL**:
   ```
   redis://default:PASSWORD@ENDPOINT:6379
   ```

### 2.3 Verify
```bash
# Test connection
redis-cli -u redis://default:PASSWORD@ENDPOINT:6379 PING
# Should return: PONG
```

---

## Step 3: Render (Backend + Celery)

### 3.1 Connect Repository
1. Go to [render.com](https://render.com) and sign up
2. Click **New +** → **Blueprint**
3. Connect GitHub:
   - **Repository**: `dutchkemsystems/dutchkem-fortress-suite`
   - **Branch**: `feature/marketing-automation`
4. Render detects `render.yaml` automatically

### 3.2 Blueprint Will Create
- `dutchkem-backend` — Django web service
- `dutchkem-celery-worker` — Background task worker
- `dutchkem-celery-beat` — Scheduled task runner
- `dutchkem-postgres` — PostgreSQL database

### 3.3 Configure Environment Variables
After blueprint creation, go to each service and set:

**dutchkem-backend:**
| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Auto-generated (or set your own) |
| `DEBUG` | `0` |
| `DJANGO_SETTINGS_MODULE` | `config.settings_production` |
| `USE_SQLITE` | `0` |
| `DB_ENGINE` | `django.db.backends.postgresql` |
| `DATABASE_URL` | From Supabase (override Render's DB) |
| `REDIS_URL` | From Upstash |
| `ALLOWED_HOSTS` | `.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | `https://your-vercel-url.vercel.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://your-vercel-url.vercel.app` |
| `CELERY_BROKER_URL` | Same as `REDIS_URL` |
| `MT5_MCP_URL` | `https://mcp.dutchkem.com` |

### 3.4 Post-Deploy
```bash
# In Render Shell tab:
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --no-input
```

### 3.5 Your Backend URL
```
https://dutchkem-backend.onrender.com
```

---

## Step 4: Vercel (Frontend)

### 4.1 Import Project
1. Go to [vercel.com](https://vercel.com) and sign up with GitHub
2. Click **Import Project**
3. Select `dutchkemsystems/dutchkem-fortress-suite`

### 4.2 Configure
| Setting | Value |
|---------|-------|
| Framework | Create React App |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Output Directory | `build` |

### 4.3 Environment Variables
| Variable | Value |
|----------|-------|
| `REACT_APP_API_URL` | `https://dutchkem-backend.onrender.com/api/v1` |
| `REACT_APP_WS_URL` | `wss://dutchkem-backend.onrender.com/ws` |

### 4.4 Deploy
Click **Deploy** and wait for build to complete.

### 4.5 Your Frontend URL
```
https://dutchkem-frontend.vercel.app
```

### 4.6 Update CORS
After getting your Vercel URL, update Render env vars:
```
CORS_ALLOWED_ORIGINS=https://dutchkem-frontend.vercel.app
CSRF_TRUSTED_ORIGINS=https://dutchkem-frontend.vercel.app
```

---

## Step 5: Cloudflare Tunnel (MT5 Bridge)

### 5.1 Install cloudflared
```bash
# Windows
winget install Cloudflare.cloudflared

# macOS
brew install cloudflare/cloudflare/cloudflared

# Linux
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
```

### 5.2 Authenticate
```bash
cloudflared tunnel login
# Opens browser — select your domain
```

### 5.3 Create Tunnel
```bash
cloudflared tunnel create dutchkem-mcp
# Copy the UUID from output
```

### 5.4 Configure
Copy `cloudflared/config.yml` to `~/.cloudflared/config.yml`:
```bash
cp cloudflared/config.yml ~/.cloudflared/config.yml
# Edit and replace <TUNNEL_UUID> with your actual UUID
```

### 5.5 Route DNS
```bash
cloudflared tunnel route dns dutchkem-mcp mcp.dutchkem.com
cloudflared tunnel route dns dutchkem-mcp mcp-ws.dutchkem.com
```

### 5.6 Run Tunnel
```bash
# Direct run
cloudflared tunnel run dutchkem-mcp

# Or with Docker Compose
docker compose -f docker/mcp-tunnel-compose.yml up -d
```

### 5.7 Your MCP Bridge URL
```
https://mcp.dutchkem.com
```

---

## Step 6: Post-Deployment Checklist

### 6.1 Backend Configuration
- [ ] Set `DEBUG=0`
- [ ] Generate secure `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` with Render URL
- [ ] Set `DATABASE_URL` from Supabase
- [ ] Set `REDIS_URL` from Upstash
- [ ] Set `CORS_ALLOWED_ORIGINS` with Vercel URL
- [ ] Run migrations
- [ ] Create superuser
- [ ] Test API endpoints

### 6.2 Frontend Configuration
- [ ] Set `REACT_APP_API_URL`
- [ ] Set `REACT_APP_WS_URL`
- [ ] Test login flow
- [ ] Test WebSocket connection

### 6.3 MT5 Bridge
- [ ] Start MT5 on your machine
- [ ] Start MCP bridge server
- [ ] Start Cloudflare tunnel
- [ ] Test connection from backend

### 6.4 Monitoring
- [ ] Set up UptimeRobot (free 50 monitors)
- [ ] Set up Sentry (free 5K errors/month)
- [ ] Configure Render health checks

---

## URLs After Deployment

| Service | URL |
|---------|-----|
| Frontend | `https://dutchkem-frontend.vercel.app` |
| Backend API | `https://dutchkem-backend.onrender.com/api/v1/` |
| API Docs | `https://dutchkem-backend.onrender.com/swagger/` |
| Admin Panel | `https://dutchkem-backend.onrender.com/admin/` |
| MCP Bridge | `https://mcp.dutchkem.com` |
| Health Check | `https://dutchkem-backend.onrender.com/api/v1/health/` |

---

## Troubleshooting

### Backend Won't Start
```bash
# Check Render logs
# Common issues:
# 1. Missing SECRET_KEY
# 2. DATABASE_URL not set
# 3. Redis connection failed
```

### Database Connection Error
```bash
# Verify Supabase URL format:
# postgresql://postgres.[REF]:[PASS]@aws-0-[REGION].pooler.supabase.com:6543/postgres

# Test connection:
psql "postgresql://postgres.xxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
```

### Celery Not Processing
```bash
# Verify Redis URL in Render env vars
# Check worker logs in Render dashboard
# Ensure CELERY_BROKER_URL matches REDIS_URL
```

### Frontend Can't Reach API
```bash
# Check CORS_ALLOWED_ORIGINS in Render
# Verify REACT_APP_API_URL in Vercel
# Ensure backend is not sleeping (Render free tier spins down)
```

### MT5 Bridge Not Connecting
```bash
# Check cloudflared tunnel status
# Verify MT5 is running locally
# Test: curl https://mcp.dutchkem.com/health
```

---

## Quick Reference Commands

```bash
# Deploy everything
bash scripts/deploy-cloud.sh all

# Deploy backend only
bash scripts/deploy-cloud.sh backend

# Deploy frontend only
bash scripts/deploy-cloud.sh frontend

# Check status
bash scripts/deploy-cloud.sh status

# Show env vars
bash scripts/deploy-cloud.sh env

# Setup guides
bash scripts/deploy-cloud.sh setup-db
bash scripts/deploy-cloud.sh setup-redis
bash scripts/deploy-cloud.sh setup-mcp
```
