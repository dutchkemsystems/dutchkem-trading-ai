# Semantic Memories — Dutchkem Trading AI

## sem-001: Django Backend Architecture
- 11 Django apps: accounts, trading, indicators, signals, risk_management, payments, expert_advisors, mcp_integration, market_data, notifications, analytics
- REST framework with JWT auth, Swagger docs, CORS headers
- Tags: backend, django, architecture

## sem-002: React Frontend Stack
- React 18, MUI Material UI v5, Redux Toolkit, Recharts, TradingView widget
- react-router-dom v6 with protected routes
- Tags: frontend, react, mui, redux

## sem-003: React Native Mobile
- Expo SDK 49, React Navigation v6, Redux, react-native-paper, react-native-chart-kit
- Tags: mobile, react-native, expo

## sem-004: Authentication System
- JWT via djangorestframework-simplejwt (30min access, 7d refresh, rotate+blacklist)
- MFA via django-otp TOTP, account lockout after 5 failed attempts
- Tags: auth, jwt, mfa, security

## sem-005: Database Stack
- PostgreSQL + TimescaleDB (time-series), Redis (caching/channels), InfluxDB (market data)
- Celery + django-celery-beat for async tasks
- Tags: database, timescaledb, redis, influxdb, celery

## sem-006: Real-time & Integration
- Django Channels + channels-redis for WebSocket live prices
- MT5 integration via MCP servers (SYNX-MT5-MCP)
- Tags: websocket, channels, mt5, mcp

## sem-007: Payment Gateway Status
- Currently: Stripe, Paystack, Flutterwave gateways configured
- Required: Replace with Korapay for African payment processing (NGN, GHS, KES, ZAR)
- Tags: payments, korapay, africa

## sem-008: Trading Risk Configuration
- MAX_DRAWDOWN=15%, MAX_DAILY_LOSS=3%, MAX_POSITION_SIZE=2%
- TARGET_ANNUAL_GROWTH=40%, MIN_RISK_REWARD_RATIO=2.0
- Tags: trading, risk, config

## sem-009: Frontend Mock Data Status
- ALL 10 pages show hardcoded mock data, need wiring to real API
- API service file exists with full endpoint definitions
- Tags: frontend, mock-data, api-wiring

## sem-010: DevOps Infrastructure
- Docker Compose production config, Railway deployment, GitHub Actions CI/CD skeleton
- Tags: devops, docker, railway, ci-cd
