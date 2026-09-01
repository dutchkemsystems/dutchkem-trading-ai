# DUTCHKEM TRADING AI - V6.5 DEPLOYMENT CHECKLIST

## Pre-Deployment Verification

- [x] Duplicate 0006 migrations removed (kept `0006_alter_tradingsettings_active_symbols.py`)
- [x] Migration chain intact: 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007
- [x] celery.py, wsgi.py, asgi.py default to `config.settings_production`
- [x] ML packages uncommented: xgboost, tensorflow, deap
- [x] Stale files cleaned: django_err.log, django_out.log, db.sqlite3
- [x] .gitignore updated: added db.sqlite3 and reports/
- [x] start-v65.ps1 script created
- [x] All V6.5 enhancement files committed

## Deployment Steps

### Step 1: Environment Setup
```bash
# Clone repository
git clone <repo-url>
cd dutchkem-trading-ai

# Copy and configure environment
cp .env.example .env
# Edit .env with production values:
#   - SECRET_KEY=<generate-new>
#   - DATABASE_URL=<postgresql-connection>
#   - REDIS_URL=<redis-connection>
#   - MT5_HOST=<mt5-bridge-host>
#   - MT5_LOGIN=<your-mt5-login>
#   - MT5_PASSWORD=<your-mt5-password>
#   - MT5_SERVER=<your-mt5-server>
```

### Step 2: Local Development Start
```powershell
# Quick start with Docker (PostgreSQL + Redis)
docker-compose up -d postgres redis

# Run migrations
cd backend
python manage.py migrate
python manage.py createsuperuser

# Start V6.5 system
cd ..
powershell -File scripts/start-v65.ps1
```

### Step 3: Production Deployment (Render)
```bash
# Push to trigger auto-deploy
git push origin main

# Or manual deploy
render deploy
```

### Step 4: Post-Deployment Verification
```bash
# Check health endpoint
curl https://dutchkem-trading-ai.onrender.com/health/

# Check API
curl https://dutchkem-trading-ai.onrender.com/api/v1/

# Check admin
open https://dutchkem-trading-ai.onrender.com/admin/
```

### Step 5: MT5 Bridge Setup
```powershell
# Setup MT5 bridge on Windows machine
powershell -File scripts/setup-mt5-bridge.ps1

# Start MT5 connection
powershell -File scripts/start-mt5.ps1
```

### Step 6: Verify V6.5 Trading Engine
```powershell
# Run virtual simulation
powershell -File scripts/virtual-100-sim.ps1 -InitialBalance 100 -SimulationDays 30

# Check V6.5 status
python backend/manage.py shell -c "
from ml.v65_orchestrator import V65Orchestrator
o = V65Orchestrator()
print(o.get_status())
"
```

## Service Architecture

| Service | Port | Description |
|---------|------|-------------|
| Django Web | 8000 | REST API + Admin |
| Celery Worker | - | Trading cycles, signals |
| Celery Beat | - | Periodic task scheduler |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache + Celery broker |
| MT5 Bridge | 8082 | MetaTrader 5 REST |
| MT5 WebSocket | 8081 | MetaTrader 5 WS |

## V6.5 Phase Pipeline

| Phase | Name | Description |
|-------|------|-------------|
| 0 | Market Scanner | Scan all 28 symbols |
| 1 | Data Ingestion | Fetch OHLCV data |
| 2 | Regime Detection | Detect market regime |
| 3 | Technical Analysis | Calculate indicators |
| 4 | Pattern Recognition | CNN pattern detection |
| 5 | Multi-Timeframe | Cross-timeframe analysis |
| 6 | Sentiment | Market sentiment analysis |
| 7 | Order Flow | Volume analysis |
| 8 | AI Prediction | LSTM ensemble prediction |
| 9 | Signal Generation | Generate trade signals |
| 10 | Risk Assessment | Position sizing |
| 11 | Correlation Check | Avoid correlated trades |
| 12 | News Filter | Economic calendar filter |
| 13 | Trade Execution | Place orders via MT5 |
| 14 | Position Monitor | Track open positions |
| 15 | Performance | Track daily performance |
| 16 | Profit Targets | Dynamic target management |

## Troubleshooting

### Migration Errors
```bash
# Check migration status
python manage.py showmigrations risk_management

# Fake if needed (DANGEROUS - only for recovery)
python manage.py migrate risk_management 0006 --fake
```

### Celery Issues
```bash
# Check worker status
celery -A config.celery inspect ping

# Check registered tasks
celery -A config.celery inspect registered

# Purge all tasks (CAUTION)
celery -A config.celery purge
```

### MT5 Bridge Issues
```bash
# Test MT5 connection
curl http://localhost:8082/health

# Check MT5 logs
Get-Content mt5-bridge\logs\*.log -Tail 50
```

## Rollback Procedure

1. Revert to last known good commit:
   ```bash
   git log --oneline -10
   git checkout <good-commit-hash>
   ```

2. Re-run migrations if schema changed:
   ```bash
   python manage.py migrate
   ```

3. Restart services:
   ```powershell
   powershell -File scripts/stop-local.ps1
   powershell -File scripts/start-v65.ps1
   ```

## Support

- **Repository:** https://github.com/dutchkem/dutchkem-trading-ai
- **Issues:** https://github.com/dutchkem/dutchkem-trading-ai/issues
- **Docs:** docs/V6.5-GUIDE.md, docs/PROFIT-GUIDE.md
