# Dutchkem Trading AI — Setup Guide

## Prerequisites

- **Python 3.10+**
- **Docker Desktop** (for PostgreSQL, Redis, MT5 bridge)
- **MetaTrader 5** terminal (for live trading)
- **ICMarkets** account (or compatible MT5 broker)
- **Git**

## Quick Start

```bash
git clone https://github.com/your-org/dutchkem-trading-ai.git
cd dutchkem-trading-aI
cp .env.example .env          # Edit .env with your values
docker compose up -d           # Start PostgreSQL + Redis + Django
python manage.py migrate       # Apply database migrations
python manage.py createsuperuser  # Create admin user
python manage.py runserver     # Start dev server at http://localhost:8000
```

## Local Development (SQLite Mode)

No Docker required for basic development:

```bash
cp .env.example .env
# Set USE_SQLITE=1 in .env (default)
pip install -r backend/requirements.txt
python manage.py migrate
python manage.py runserver
```

Uses SQLite database. Background tasks (Celery) require Redis — skip them for UI/API work.

## MT5 Bridge Setup

The MT5 bridge connects Django to MetaTrader 5 via Docker. See [mt5-bridge/README.md](mt5-bridge/README.md) for full details.

```bash
cd mt5-bridge
cp .env.example .env
docker compose up -d
# Bridge exposes REST on port 8082, WebSocket on port 8081
```

## Production Deployment (Render)

The project includes `render.yaml` for one-click Render deployment:

1. Push to GitHub
2. Connect repo to Render
3. Render auto-detects `render.yaml` and provisions:
   - Web service (Django + gunicorn)
   - PostgreSQL database
4. Set required environment variables in Render dashboard
5. Deploy

See `DEPLOY_RENDER.md` for detailed steps.

## Environment Variables

### Django Core
| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | Django secret key |
| `DEBUG` | `0` | Debug mode (set `1` for dev) |
| `DJANGO_SETTINGS_MODULE` | `config.settings_production` | Settings module |
| `USE_SQLITE` | `1` | Use SQLite (1) or PostgreSQL (0) |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |

### Redis / Celery
| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery broker URL |

### MetaTrader 5 Bridge
| Variable | Default | Description |
|----------|---------|-------------|
| `MT5_HOST` | `localhost` | MT5 bridge host |
| `MT5_PORT` | `3000` | MT5 REST port |
| `MT5_WS_PORT` | `3001` | MT5 WebSocket port |
| `MT5_TIMEOUT` | `10` | Connection timeout (seconds) |
| `MT5_MAX_RETRIES` | `5` | Max retry attempts |
| `MT5_RETRY_DELAY` | `2.0` | Delay between retries (seconds) |
| `MT5_MCP_URL` | `http://localhost:8080` | MCP server URL |

### Payments (Korapay)
| Variable | Description |
|----------|-------------|
| `KORA_SECRET_KEY` | Korapay secret key |
| `KORA_ENCRYPTION_KEY` | Korapay encryption key |
| `KORA_PUBLIC_KEY` | Korapay public key |
| `KORA_WEBHOOK_SECRET` | Webhook verification secret |

### CORS / Security
| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,...` | Comma-separated CORS origins |
| `SECURE_SSL_REDIRECT` | `False` | Redirect HTTP to HTTPS |
| `SESSION_COOKIE_SECURE` | `False` | Secure session cookies |
| `CSRF_COOKIE_SECURE` | `False` | Secure CSRF cookies |

## API Endpoints

All endpoints are prefixed with `/api/v1/`.

| Module | Base Path | Description |
|--------|-----------|-------------|
| Accounts | `/api/v1/auth/` | Registration, login, token refresh, profile |
| Trading | `/api/v1/trading/` | Symbols, trades, orders, positions, portfolio |
| Indicators | `/api/v1/indicators/` | 100+ technical indicators |
| Signals | `/api/v1/signals/` | AI-generated trading signals |
| Risk Management | `/api/v1/risk/` | Daily limits, drawdown, circuit breakers |
| Payments | `/api/v1/payments/` | Deposits, withdrawals, KYC |
| Expert Advisors | `/api/v1/eas/` | EA management, MQL5 code generation |
| Market Data | `/api/v1/market/` | Real-time prices, economic calendar |
| Notifications | `/api/v1/notifications/` | Alerts, push notifications |
| Analytics | `/api/v1/analytics/` | Performance analytics, reports |
| MCP Integration | `/api/v1/mcp/` | MT5 bridge integration |
| Referrals | `/api/v1/referrals/` | Referral tracking, rewards |
| ML | `/api/v1/ml/` | Machine learning models |
| Backtesting | `/api/v1/backtesting/` | Strategy backtesting |
| Gold Edge | `/api/v1/gold-edge/` | Gold-specific trading strategies |
| Scalping | `/api/v1/scalping/` | Scalping strategies |
| Infrastructure | `/api/v1/infrastructure/` | Failover, broker switching |
| Security | `/api/v1/security/` | Zero trust, audit logs |

**Docs:**
- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`
- Health check: `/health/`
- Metrics: `/metrics/`
- Admin: `/admin/`

## Architecture Overview

The trading sequence follows 10 steps:

1. **Data Ingestion** — MT5 bridge streams tick/candle data via WebSocket
2. **Indicator Calculation** — 100+ technical indicators computed in real-time
3. **Signal Generation** — Multi-timeframe confluence scoring produces signals
4. **Risk Validation** — Daily limits, drawdown checks, position sizing
5. **Order Execution** — MT5 bridge sends orders to broker (ICMarkets)
6. **Position Monitoring** — Real-time P&L tracking, SL/TP management
7. **Analytics** — Performance metrics, win rate, Sharpe ratio
8. **Notifications** — Alerts via WebSocket, email, or push
9. **ML Feedback** — Results feed back into ML models for improvement
10. **Audit Logging** — Every action logged for compliance

## Troubleshooting

**`USE_SQLITE=1` but server can't start:**
- Ensure `requirements.txt` is installed: `pip install -r backend/requirements.txt`

**MT5 bridge not connecting:**
- Verify MT5 is running on the host machine
- Check Docker is running: `docker ps`
- Check bridge logs: `docker compose -f mt5-bridge/docker-compose.yml logs`

**Port 8000 already in use:**
- Kill the process: `lsof -ti:8000 | xargs kill -9` (Linux/Mac) or use Task Manager (Windows)

**Database migrations fail:**
- For SQLite: delete `db.sqlite3` and re-run `python manage.py migrate`
- For PostgreSQL: ensure Docker is running and the `db` service is healthy

**CORS errors in browser:**
- Add your frontend URL to `CORS_ALLOWED_ORIGINS` in `.env`
- Ensure `ALLOWED_HOSTS` includes your domain

**JWT token expired:**
- Use the refresh endpoint: `POST /api/v1/auth/token/refresh/`
- Tokens expire after the period configured in `settings.py`
