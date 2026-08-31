# Technical Architecture — Dutchkem Trading AI

## 1. System Overview

### 1.1 Three-Power Model Architecture

The Dutchkem Trading AI (DTA) platform is built on a **Three-Power Model Architecture** that separates concerns across three AI layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      THREE-POWER MODEL                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  @devhive — ORCHESTRATION LAYER                             │   │
│  │  • Task distribution across 23 agents                       │   │
│  │  • Agent coordination and dependency resolution             │   │
│  │  • Result aggregation and conflict resolution               │   │
│  │  • Pipeline orchestration (ingest → analyze → signal)       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  @gstack — TEAM LAYER (23 Specialized Agents)               │   │
│  │  • Trend Analysis Agent        • Fibonacci Analysis Agent   │   │
│  │  • Momentum Analysis Agent     • Elliott Wave Agent         │   │
│  │  • Volatility Analysis Agent   • Harmonic Pattern Agent     │   │
│  │  • Volume Analysis Agent       • Sentiment Analysis Agent   │   │
│  │  • Pattern Recognition Agent   • News Impact Agent          │   │
│  │  • Support/Resistance Agent    • Correlation Agent          │   │
│  │  • Seasonality Agent           • Market Structure Agent     │   │
│  │  • Liquidity Analysis Agent    • Order Flow Agent           │   │
│  │  • Divergence Agent            • Multi-Timeframe Agent      │   │
│  │  • Risk Assessment Agent       • Position Sizing Agent      │   │
│  │  • Exit Strategy Agent         • Backtesting Agent          │   │
│  │  • Portfolio Optimization Agent                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  @minimax — GENERATION LAYER                                │   │
│  │  • LLM-powered signal narrative generation                  │   │
│  │  • Market context interpretation                            │   │
│  │  • Multi-model consensus building                           │   │
│  │  • Natural language signal explanations                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Layer Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                                │
│  React 18 Web App │ React Native Mobile │ Admin Portal               │
│  (Vite + Redux)   │ (Expo + RN 0.72+)  │ (Django Admin)             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP/REST + WebSocket
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    API GATEWAY LAYER                                 │
│  Nginx Reverse Proxy │ Rate Limiting │ SSL Termination              │
│  Load Balancing │ Request Routing │ Static File Serving             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                                │
│  Django 4.2 REST API │ Django Channels WebSocket │ Celery Workers    │
│  JWT Auth │ RBAC │ API Versioning (/api/v1/) │ Swagger Docs         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│    APPLICATION LAYER     │  │    BACKGROUND TASKS       │
│  10 Django Apps          │  │  Celery + RabbitMQ        │
│  accounts, trading,      │  │  Signal Generation        │
│  indicators, signals,    │  │  Risk Calculations        │
│  risk_management,        │  │  MT5 Sync, Payments       │
│  payments, expert_advis. │  │  EA Backtesting           │
│  mcp_integration,        │  │  Data Ingestion           │
│  market_data, notifs     │  │  Notification Send        │
└──────────────────────────┘  └──────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│    AI AGENT LAYER        │  │    MCP INTEGRATION LAYER  │
│  @gstack 23 Agents       │  │  SYNX-MT5-MCP (68+ tools)│
│  @minimax LLM Generation │  │  OpenAlgo (100+ indic.)   │
│  LangChain Orchestration │  │  OpenTrading (Risk/Exec)  │
│  OpenAI API              │  │  CrossTrade (NinjaTrader8)│
└──────────────────────────┘  └──────────────────────────┘
                    │                       │
                    └───────────┬───────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                         │
│  PostgreSQL 16 │ TimescaleDB │ InfluxDB 2.7 │ Redis 7 │ RabbitMQ 3 │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES LAYER                            │
│  MetaTrader 5 │ Stripe │ Paystack │ PayPal │ SendGrid │ Twilio      │
│  OpenAI API │ CoinGecko │ Alpha Vantage │ Firebase │ M-Pesa         │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 Component Interaction Flow

```
MARKET DATA FLOW:
══════════════════════════════════════════════════════════════════════

  MT5 Terminal                 DTA Platform                     Traders
  ────────────                 ────────────                     ───────
       │                            │                              │
       │  Tick Data                 │                              │
       ├───────────────────────────►│                              │
       │                            │  ┌─────────────────────┐    │
       │                            │  │ InfluxDB (ticks)    │    │
       │                            │  │ TimescaleDB (OHLCV) │    │
       │                            │  └─────────────────────┘    │
       │                            │           │                  │
       │                            │           ▼                  │
       │                            │  ┌─────────────────────┐    │
       │                            │  │ @gstack 23 Agents   │    │
       │                            │  │ (parallel analysis) │    │
       │                            │  └──────────┬──────────┘    │
       │                            │             │                │
       │                            │             ▼                │
       │                            │  ┌─────────────────────┐    │
       │                            │  │ @devhive Orchestrator│    │
       │                            │  │ (aggregation)        │    │
       │                            │  └──────────┬──────────┘    │
       │                            │             │                │
       │                            │             ▼                │
       │                            │  ┌─────────────────────┐    │
       │                            │  │ @minimax LLM        │    │
       │                            │  │ (signal narrative)  │    │
       │                            │  └──────────┬──────────┘    │
       │                            │             │                │
       │                            │             ▼                │
       │                            │  ┌─────────────────────┐    │
       │                            │  │ Risk Validation     │    │
       │                            │  │ (2% max, 0.7 corr) │    │
       │                            │  └──────────┬──────────┘    │
       │                            │             │                │
       │                            │             ▼                │
       │                            │  ┌─────────────────────┐    │
       │  Order Execution           │  │ Signal Generated     │    │
       │◄───────────────────────────┤  │ (STRONG_BUY/SELL)   │───►│
       │                            │  └─────────────────────┘    │
       │  Position Update           │           │                  │
       │◄───────────────────────────┤           │                  │
       │                            │           ▼                  │
       │                            │  ┌─────────────────────┐    │
       │                            │  │ WebSocket Push      │    │
       │                            │  │ (real-time update)  │───►│
       │                            │  └─────────────────────┘    │


SIGNAL GENERATION PIPELINE:
══════════════════════════════════════════════════════════════════════

  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  INGEST  │───►│ ANALYZE  │───►│ VALIDATE │───►│ DELIVER  │
  │          │    │          │    │          │    │          │
  │ • Market │    │ • 23     │    │ • Risk   │    │ • Signal │
  │   data   │    │   agents │    │   check  │    │   push   │
  │ • News   │    │   (para) │    │ • Conf   │    │ • Notif  │
  │ • Feed   │    │ • LLM    │    │   score  │    │ • Log    │
  └──────────┘    │   narr   │    │ • R:R    │    └──────────┘
                  └──────────┘    │   ratio  │
                                  └──────────┘


RISK MANAGEMENT FLOW:
══════════════════════════════════════════════════════════════════════

  Every 15 Minutes (Celery Beat)
  ─────────────────────────────
  ┌─────────────────────────────────────────────────────────────┐
  │                    RISK CHECK CYCLE                          │
  │                                                             │
  │  1. Calculate Daily P&L                                     │
  │     └─► If daily_loss > 3% → HALT TRADING                  │
  │                                                             │
  │  2. Check Drawdown from Peak Equity                         │
  │     └─► If drawdown > 15% → HALT TRADING                   │
  │                                                             │
  │  3. Verify Position Count                                   │
  │     └─► If open_positions >= 5 → BLOCK NEW ENTRIES          │
  │                                                             │
  │  4. Validate Correlation Matrix                             │
  │     └─► If any pair correlation > 0.7 → ALERT              │
  │                                                             │
  │  5. Monitor Margin Levels                                   │
  │     ├─► < 200% → WARNING                                   │
  │     ├─► < 150% → REDUCE POSITIONS                          │
  │     └─► < 100% → CLOSE ALL POSITIONS                       │
  │                                                             │
  │  6. Update Risk Alerts (WebSocket push)                     │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```
