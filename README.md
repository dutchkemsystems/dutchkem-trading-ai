# Dutchkem Trading AI

**AI-powered forex trading system with MetaTrader 5 integration, signal generation, backtesting, and risk management.**

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
│   ├── ml/                # LSTM, regime detection
│   ├── risk_management/   # Position sizing, drawdown
│   ├── scalping/          # Scalping strategies
│   ├── signals/           # Trade signal generation
│   ├── strategies/        # Strategy framework
│   └── trading/           # Core trading engine
├── config/                # Django settings
├── strategies/            # External strategy definitions
├── scripts/               # Deployment scripts
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

## Deployment

See deployment guides:
- [Render](RENDER_DEPLOY.md)
- [Railway](RAILWAY_DEPLOY.md)
- [Fly.io](deploy-fly.ps1)

## License

Proprietary — Dutchkem Ventures Ltd.
