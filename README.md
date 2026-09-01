# Dutchkem Trading AI

**AI-powered forex trading system with MetaTrader 5 integration, signal generation, backtesting, and risk management.**

## Trading Engine: V6.5 (DEFAULT)

V6.5 is the PRIMARY trading engine featuring a comprehensive 16-phase pipeline:

- **Phase 0-16:** Market scanning, AI analysis, sentiment, order flow, pattern recognition, multi-timeframe analysis, risk management, and self-optimization
- **Backup Systems:** V6 → Gold Edge → Scalping → Confluence Engine
- **Default Mode:** Semi-auto (requires approval for trades)
- **Virtual Account:** $100 starting balance available

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      DJANGO REST API                            │
│           /api/* — trading signals, backtesting, analytics      │
├─────────┬─────────┬─────────┬─────────┬─────────────────────────┤
│ SIGNALS │  ML     │ RISK    │MARKET   │   STRATEGIES            │
│ ENGINE  │ MODELS  │MANAGER  │DATA     │   (Gold Edge, etc.)     │
├─────────┴─────────┴─────────┴─────────┴─────────────────────────┤
│                    CELERY WORKERS                                │
│         market data ingestion, signal generation, backtesting    │
├─────────────────────────────────────────────────────────────────┤
│   PostgreSQL    │    Redis    │  MetaTrader 5 Bridge            │
│  (trading data) │  (cache)    │  (MT5_HOST:MT5_PORT)            │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend:** Python 3.12+, Django, Django REST Framework
- **Database:** PostgreSQL 16 (SQLite for local dev)
- **Task Queue:** Celery + Redis
- **Trading:** MetaTrader 5 integration
- **ML:** Scikit-learn, LSTM models
- **Deployment:** Docker, Render, Fly.io, Railway

## Quick Start

```bash
# Clone and setup
git clone <repo>
cd dutchkem-trading-ai

# Local dev (SQLite)
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Docker (PostgreSQL + Redis)
docker-compose up -d
python manage.py migrate
python manage.py runserver
```

## V6.5 Quick Start

```bash
# Auto-configure V6.5
powershell -File scripts/configure-v65.ps1 -TradingMode semi -VirtualBalance 100

# Start V6.5 full stack (Docker + Django + Celery + MT5 Bridge)
powershell -File scripts/start-v65.ps1

# Run virtual $1000 simulation
powershell -File scripts/virtual-1000-sim.ps1 -InitialBalance 1000 -SimulationDays 30

# Run virtual $100 simulation
powershell -File scripts/virtual-100-sim.ps1 -InitialBalance 100 -SimulationDays 30
```

## Project Structure

```
dutchkem-trading-ai/
├── backend/
│   ├── accounts/          # User management
│   ├── analytics/         # Performance analytics
│   ├── backtesting/       # Strategy backtesting engine
│   ├── expert_advisors/   # MT5 EA integration
│   ├── gold_edge/         # Gold trading strategy
│   ├── indicators/        # Technical indicators
│   ├── market_data/       # Price data ingestion
│   ├── ml/                # LSTM, regime detection, V6.5 orchestrator
│   │   ├── v65_orchestrator.py  # V6.5 PRIMARY trading engine
│   │   ├── v6_orchestrator.py   # V6 fallback
│   │   └── enhancements/        # V6.5 enhancements (11 modules)
│   ├── risk_management/   # Position sizing, drawdown
│   ├── scalping/          # Scalping strategies
│   ├── signals/           # Trade signal generation
│   ├── strategies/        # Strategy framework
│   └── trading/           # Core trading engine
├── config/                # Django settings
├── scripts/               # Deployment & simulation scripts
│   ├── virtual-1000-sim.ps1     # V6.5 $1000 simulation
│   ├── virtual-100-sim.ps1      # V6.5 $100 simulation
│   ├── virtual-trading-sim.ps1  # Generic trading simulation
│   ├── configure-v65.ps1        # V6.5 auto-configuration
│   └── start-v65.ps1            # V6.5 full stack startup
├── docs/
│   └── V6.5-GUIDE.md     # Complete V6.5 documentation
├── strategies/            # External strategy definitions
├── fly.toml               # Fly.io config
├── render.yaml            # Render config
└── railway.json           # Railway config
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | - | Django secret key |
| `DEBUG` | `0` | Debug mode (1=on, 0=off) |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `MT5_HOST` | `localhost` | MetaTrader 5 bridge host |
| `MT5_PORT` | `8082` | MetaTrader 5 REST port |
| `MT5_WS_PORT` | `8081` | MetaTrader 5 WebSocket port |
| `USE_SQLITE` | `1` | Use SQLite instead of PostgreSQL |
| `TRADING_ENGINE` | `v6.5` | Trading engine (v6.5, v6, gold_edge, scalping) |
| `TRADING_MODE` | `semi` | Trading mode (manual, semi, full) |
| `VIRTUAL_ACCOUNT_BALANCE` | `100.0` | Virtual account balance for simulation |

## Deployment

See deployment guides:
- [Deployment Checklist](DEPLOY-CHECKLIST.md) — step-by-step production deployment
- [Render](RENDER_DEPLOY.md)
- [Railway](RAILWAY_DEPLOY.md)
- [Fly.io](deploy-fly.ps1)
- [V6.5 Guide](docs/PROFIT-GUIDE.md) — profit targets and trading simulation

## License

Proprietary — Dutchkem Ventures Ltd.
