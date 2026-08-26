# Dutchkem Trading AI

## Overview

A comprehensive, production-grade forex trading platform with multi-timeframe analysis, AI signal generation, and daily-focused risk management.

## Features

- **6 Timeframes**: M5, M15, M30, H1, H2, H4
- **100+ Indicators**: RSI, MACD, EMA, Bollinger Bands, and more
- **AI Signals**: Multi-timeframe confluence scoring
- **Risk Management**: 2% max daily loss, 0.14% daily growth target
- **Expert Advisors**: MQL5 code generation
- **MCP Integration**: SYNX-MT5, AkTools, OpenAlgo, CrossTrade, OpenTrading
- **Multi-Gateway Payments**: Bank Transfer, Card, Crypto, PayPal, Mobile Money
- **Real-Time WebSocket**: Live price updates, signal alerts
- **Analytics Dashboard**: P&L charts, risk metrics, signal performance

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/dutchkem/dutchkem-trading-ai.git
cd dutchkem-trading-ai
cp .env.example .env
```

### 2. Docker Setup

```bash
cd docker
docker-compose up -d
```

### 3. Access the Platform

- **Web App**: http://localhost
- **API**: http://localhost/api/v1/
- **Swagger Docs**: http://localhost/swagger/
- **Admin**: http://localhost/admin/

## Project Structure

```
dutchkem-trading-ai/
├── backend/                    # Django backend
│   ├── accounts/              # User management, JWT, MFA
│   ├── trading/               # Symbols, trades, orders
│   ├── indicators/            # 100+ technical indicators
│   ├── signals/               # AI signal generation
│   ├── risk_management/       # Daily risk limits, circuit breakers
│   ├── payments/              # Multi-gateway payments
│   ├── expert_advisors/       # EA management, MQL5 generation
│   ├── mcp_integration/       # MCP server connectivity
│   ├── market_data/           # Real-time prices, WebSocket
│   ├── notifications/         # Push, email, SMS alerts
│   ├── analytics/             # Trading analytics & metrics
│   └── config/                # Settings, Celery, WebSocket
├── frontend/                   # React web app
│   ├── src/pages/             # Dashboard, Trading, Signals, etc.
│   ├── src/features/          # Redux slices
│   └── src/services/          # API service layer
├── mobile/                     # React Native app
│   └── screens/               # Dashboard, Trading, Signals, Analytics
├── strategies/                 # Trading strategies
│   ├── timeframe_strategies.py  # M5-H4 strategies
│   ├── risk_manager.py        # DailyRiskManager class
│   └── confluence.py          # Multi-timeframe confluence
├── eas/                        # Expert Advisors
│   └── mql5_generator.py      # MQL5 code generator
├── mcp-servers/                # MCP integration
│   └── mcp_service.py         # Unified MCP service
├── docker/                     # Docker configurations
│   ├── docker-compose.yml     # Development
│   ├── docker-compose.prod.yml  # Production
│   └── nginx/                 # Reverse proxy
├── .github/workflows/         # CI/CD pipeline
└── docs/                       # Documentation
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login/` — Login
- `POST /api/v1/auth/register/` — Register
- `POST /api/v1/auth/logout/` — Logout
- `POST /api/v1/auth/refresh/` — Refresh token

### Trading
- `GET /api/v1/trading/symbols/` — List symbols
- `GET /api/v1/trading/trades/` — List trades
- `POST /api/v1/trading/orders/create/` — Create order

### Signals
- `GET /api/v1/signals/` — List signals
- `GET /api/v1/signals/active/` — Active signals
- `POST /api/v1/signals/generate/` — Generate signal

### Risk Management
- `GET /api/v1/risk/parameters/` — Risk parameters
- `GET /api/v1/risk/drawdown/status/` — Drawdown status
- `POST /api/v1/risk/position-sizing/` — Calculate position size

### Analytics
- `GET /api/v1/analytics/performance/` — Trading performance
- `GET /api/v1/analytics/risk/` — Risk analytics
- `GET /api/v1/analytics/signals/` — Signal analytics

### WebSocket
- `ws://localhost/ws/market-data/{symbol}/` — Live prices
- `ws://localhost/ws/signals/` — Signal updates
- `ws://localhost/ws/trades/` — Trade updates
- `ws://localhost/ws/portfolio/` — Portfolio updates

## Risk Rules

| Parameter | Value |
|-----------|-------|
| Daily Growth Target | 0.14% |
| Max Daily Loss | 2% |
| Max Drawdown | 15% |
| Position Size | 1% per trade |
| Max Daily Trades | 10 |
| Daily Target Lock | 0.4% |
| Min Risk-Reward | 1:2 |

## Tech Stack

- **Backend**: Django 4.2, DRF, Celery, PostgreSQL, Redis, InfluxDB
- **Frontend**: React 18, Redux, Material-UI, TradingView
- **Mobile**: React Native, Expo
- **Infrastructure**: Docker, Nginx, Prometheus, Grafana
- **Testing**: pytest, coverage

## Testing

```bash
cd backend
pytest -v --tb=short
```

## License

Proprietary - Dutchkem Trading AI
