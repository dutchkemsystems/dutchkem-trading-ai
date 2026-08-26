# Dutchkem Trading AI — Project Context

## Platform Overview
Dutchkem Trading AI (DTA) is a comprehensive, production-grade web and mobile trading platform that leverages the Three-Power Model Architecture to trade major, minor, and commodity forex pairs across all timeframes (M5 to H4).

## Three-Power Model Architecture
1. **@devhive — Orchestration Layer**: Autonomous AI Software Pipeline with Skill-Driven Development (SDD). Includes Planner, Router, Quality, and Export agents plus 6 timeframe-specific planner agents.

2. **@gstack — Role-Based Team Layer**: Virtual Engineering Team with 23 specialized roles including CEO, Designer, Engineering Manager, Release Manager, QA, Security, Product, Data Scientist, Infrastructure agents, plus 6 timeframe specialist agents (M5, M15, M30, H1, H2, H4).

3. **@minimax — Generation Engine**: Frontier Coding Model with 1M context window. MiniMax-M3 for strategy generation and full platform code. MiniMax-M2.7 for EA optimization and code refactoring.

## Performance Targets (Daily Focused)
| Metric | Target |
|--------|--------|
| Daily Equity Growth | 0.14% per day (40% annualized / 365) |
| Monthly Equity Growth | ~4.2% per month |
| Annual Equity Growth | ~50%+ per year (compounded daily) |
| Max Drawdown | <15% |
| Max Daily Loss | 2% |
| Max Position Size | 1% per trade |
| Max Daily Trades | 10 |
| Daily Target Lock | Trading stops at 0.4% daily gain |
| Win Rate | >55% |
| Risk-Reward Ratio | 1:2 minimum |
| Sharpe Ratio | >1.5 |

## Supported Timeframes
| Timeframe | Strategy | Daily Trades | Win Rate | Risk-Reward | Daily Growth |
|-----------|----------|--------------|----------|-------------|--------------|
| M5 | Scalping | 5-10 | 60-65% | 1:1.5 | 1-2% |
| M15 | Momentum | 3-5 | 58-63% | 1:1.8 | 0.8-1.5% |
| M30 | Swing | 2-3 | 55-60% | 1:2 | 0.5-1% |
| H1 | Trend | 1-2 | 52-58% | 1:2.5 | 0.3-0.6% |
| H2 | Position | 0-1 | 50-55% | 1:3 | 0.2-0.4% |
| H4 | Strategic | 0-1 | 48-52% | 1:4 | 0.1-0.3% |

## Implementation Phases
1. Phase 1: Foundation (3 weeks)
2. Phase 2: @devhive Orchestration (2 weeks)
3. Phase 3: @gstack Team Deployment (3 weeks)
4. Phase 4: @minimax Generation (2 weeks)
5. Phase 5: Indicator & Signal Engine (3 weeks)
6. Phase 6: Risk Management Engine (2 weeks)
7. Phase 7: Payment & Withdrawal System (2 weeks)
8. Phase 8: Expert Advisor Engine (2 weeks)
9. Phase 9: Frontend Development (3 weeks)
10. Phase 10: Testing & Deployment (2 weeks)

## Directory Structure
```
dutchkem-trading-ai/
├── backend/          # Django backend (10 apps)
├── frontend/         # React web app
├── mobile/           # React Native app
├── docker/           # Docker configurations
├── mcp-servers/      # MCP server implementations
├── eas/              # Expert Advisor files
├── strategies/       # Trading strategies
└── .devhive/         # DevHive memory and specs
```

## Backend Apps
1. accounts - User management, authentication, KYC
2. trading - Symbols, trades, orders, positions
3. indicators - 100+ technical indicators
4. signals - AI signal generation, confluence scoring
5. risk_management - Daily risk limits, circuit breakers
6. payments - Multi-gateway deposits/withdrawals
7. expert_advisors - EA management, MQL5 generation
8. mcp_integration - SYNX-MT5-MCP, AkTools, OpenAlgo
9. market_data - Real-time prices, WebSocket consumers
10. notifications - Push, email, SMS alerts
