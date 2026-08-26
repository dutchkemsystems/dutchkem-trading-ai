# Phase 03: Architecture

## Executive Summary

Dutchkem Fortress Suite uses a **monolithic modular architecture** with a unified billing engine ("Agentic Fuel") at its core. The platform is built on FastAPI (async Python), PostgreSQL, Celery/Redis, and React — deployed to Kubernetes clusters in Africa and Europe.

## Architecture Pattern

**Modular Monolith** with clear domain boundaries:
- All 5 pillars share the same FastAPI application
- Each pillar has its own API router, models, and services
- The billing engine (Pillar 0) is a shared service consumed by all pillars
- Celery workers handle async metering, billing, and fraud detection
- PostgreSQL provides ACID transactions for financial data

## UX/UI & Design System

**Admin Dashboard Design System:**
- **Primary:** Forest green (#22c55e) — trust, growth
- **Accent:** Gold (#eab308) — premium, value
- **Background:** Deep navy (#030712) — security, authority
- **Typography:** Space Grotesk (display), Inter (body), JetBrains Mono (data)
- **Layout:** Fixed sidebar + scrollable main content
- **Cards:** Rounded-2xl, glass-morphism with backdrop blur

## Components & Modules

### Core (Pillar 0)
- **BillingService:** Credit ledger, wallet management, invoicing
- **MeteringService:** Agent task recording, execution tracking
- **FXService:** Real-time exchange rate fetching, credit pegging
- **PaymentService:** Provider routing (Paystack/Flutterwave/Stripe)

### Pillar 1: Afro-Pay
- **RemittanceService:** Cross-border transfer orchestration
- **StablecoinService:** USDT/USDC on/off-ramp management

### Pillar 2: Sentinel Africa
- **ThreatService:** Alert creation, escalation, neutralization
- **AgentOrchestrator:** Recon/Simulation/Response/Log agent coordination

### Pillar 3: African Agent Cloud
- **DeploymentService:** Agent provisioning, lifecycle management
- **LanguageService:** Multi-language agent configuration

### Pillar 4: NetraID
- **VerificationService:** Biometric, liveness, document verification
- **ComplianceService:** NDPA/POPIA compliance management

### Pillar 5: TrustNode
- **RouterService:** Model selection, fallback chains, cost optimization

## Data Architecture & Models

### Core Tables
- **clients** — Client accounts with tier, country, status
- **client_wallets** — Credit balances, auto-topup config
- **credit_transactions** — Immutable double-entry ledger
- **invoices** — Generated billing statements

### Agent Tables
- **agents** — Agent registry with pillar, cost
- **agent_tasks** — Task type definitions with credit costs
- **agent_executions** — Immutable metering log

### FX & Payments
- **fx_rates** / **fx_rate_history** — Exchange rate tracking
- **payment_providers** / **payment_transactions** — Payment integration

### Pillar Tables
- **afropay_transactions** — Remittance records
- **sentinel_agents** / **sentinel_alerts** — SOC monitoring
- **agent_cloud_deployments** — AI agent instances
- **netra_id_verifications** — Identity verification log
- **trustnode_requests** — AI abstraction routing log

**Total: 16 tables, 8 ENUM types, 15 indexes**

## APIs / Interfaces

### Authentication
- `POST /api/v1/auth/register` — Client registration
- `POST /api/v1/auth/login` — JWT authentication

### Billing (Pillar 0)
- `GET /api/v1/billing/balance` — Credit balance
- `POST /api/v1/billing/deduct` — Deduct credits
- `POST /api/v1/billing/topup` — Top up credits
- `PUT /api/v1/billing/auto-topup` — Configure auto-topup
- `GET /api/v1/billing/transactions` — Transaction history
- `POST /api/v1/billing/invoices/generate` — Generate invoice

### Metering
- `GET /api/v1/metering/agents` — List agents
- `POST /api/v1/metering/execute` — Execute & charge agent task
- `GET /api/v1/metering/usage` — Usage statistics

### Payments
- `POST /api/v1/payments/paystack/webhook` — Paystack webhook
- `POST /api/v1/payments/flutterwave/webhook` — Flutterwave webhook
- `POST /api/v1/payments/stripe/webhook` — Stripe webhook

### Pillar APIs
- `POST /api/v1/afropay/send` — Send remittance
- `POST /api/v1/sentinel/scan` — Initiate threat scan
- `POST /api/v1/agents/deploy` — Deploy AI agent
- `POST /api/v1/netra-id/verify` — Verify identity
- `POST /api/v1/trust-node/generate` — Route AI request

### Admin
- `GET /api/v1/admin/dashboard` — Revenue metrics
- `GET /api/v1/admin/pillar-breakdown` — Per-pillar revenue
- `GET /api/v1/admin/clients` — Client metrics

## Infrastructure & Deployment

- **Primary Region:** AWS Cape Town (af-south-1) — Africa
- **Secondary Region:** AWS Frankfurt (eu-central-1) — Europe/GDPR
- **Orchestration:** Kubernetes (EKS) with HPA auto-scaling
- **Database:** RDS PostgreSQL 16 with Multi-AZ, 50GB storage
- **Cache:** ElastiCache Redis 7 with encryption at rest
- **CI/CD:** GitHub Actions → Docker → ECR → Kubernetes
- **IaC:** Terraform with S3 backend + DynamoDB locking
- **Security:** Zero-Trust, mTLS, OWASP Top 10, NDPA/POPIA compliant
