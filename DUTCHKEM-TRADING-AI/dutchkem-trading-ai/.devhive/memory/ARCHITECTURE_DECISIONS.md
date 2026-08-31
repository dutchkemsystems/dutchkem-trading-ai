# Architecture Decisions — Dutchkem Trading AI

## AD-001: Multi-Layer Architecture
- **Decision**: Use 6-layer architecture (Presentation, Orchestration, Team, Generation, MCP, Execution)
- **Rationale**: Separates concerns for AI orchestration, team management, code generation, MCP integration, and trade execution
- **Status**: Accepted

## AD-002: Database Strategy
- **Decision**: PostgreSQL 16 + TimescaleDB for relational + time-series data, InfluxDB for real-time metrics, Redis for caching
- **Rationale**: TimescaleDB handles market data hypertables efficiently, InfluxDB for high-frequency metrics, Redis for session/cache
- **Status**: Accepted

## AD-003: Authentication
- **Decision**: JWT with SimpleJWT, TOTP-based MFA, RBAC roles (TRADER, ADMIN, MANAGER, VIEWER)
- **Rationale**: Industry standard for API auth, MFA for security, RBAC for access control
- **Status**: Accepted

## AD-004: Real-Time Communication
- **Decision**: Django Channels with WebSocket for real-time market data, signals, and trade updates
- **Rationale**: Low-latency push updates for trading platform requirements
- **Status**: Accepted

## AD-005: Async Processing
- **Decision**: Celery 5.3 with RabbitMQ broker for background tasks (indicator calculation, signal generation, EA deployment)
- **Rationale**: Reliable message broker, excellent Django integration, task scheduling with django-celery-beat
- **Status**: Accepted

## AD-006: MCP Integration
- **Decision**: Abstract MCP server connections through a unified integration layer
- **Rationale**: Allows swapping MCP servers without changing core logic, supports SYNX-MT5-MCP, AkTools, OpenAlgo, CrossTrade, OpenTrading
- **Status**: Accepted

## AD-007: Multi-Timeframe Confluence
- **Decision**: Implement hierarchical timeframe analysis (H4 → H1 → M15 → entry)
- **Rationale**: Higher timeframe trend direction guides lower timeframe entries, improves win rate
- **Status**: Accepted

## AD-008: Risk Management (Daily Focused)
- **Decision**: Daily risk limits with circuit breakers: 2% max daily loss, 0.14% daily target, 0.4% daily target lock, 15% max drawdown
- **Rationale**: Tight daily monitoring enables faster drawdown recovery, consistent compounding, prevents catastrophic losses
- **Status**: Accepted

## AD-009: Position Sizing
- **Decision**: 1% risk per trade (reduced from 2%) to stay within daily 2% loss limit
- **Rationale**: Allows 2 losing trades before hitting daily loss limit, more conservative approach
- **Status**: Accepted

## AD-010: Payment Processing
- **Decision**: Gateway abstraction layer supporting Paystack, Flutterwave, Stripe, Coinbase, Mobile Money
- **Rationale**: Multi-region support, fallback options, unified transaction handling
- **Status**: Accepted

## AD-011: Frontend Architecture
- **Decision**: React 18 with Redux Toolkit, TradingView charts, React Native for mobile
- **Rationale**: Component-based UI, efficient state management, professional charting, cross-platform mobile
- **Status**: Accepted

## AD-012: Daily Performance Tracking
- **Decision**: Track daily performance metrics including P&L, win rate, risk-reward ratio per timeframe
- **Rationale**: Enables daily optimization, performance accountability, and strategy refinement
- **Status**: Accepted
