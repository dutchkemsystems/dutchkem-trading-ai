# Dutchkem Fortress Suite

**Multi-layered, monetized SaaS platform for Africa and the global diaspora.**

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADMIN DASHBOARD (React)                       │
│              Real-time metrics, wallet, agents                   │
├─────────────────────────────────────────────────────────────────┤
│                     FASTAPI API GATEWAY                          │
│              /api/v1/* — REST endpoints                         │
├─────────┬─────────┬─────────┬─────────┬─────────┬───────────────┤
│ PILLAR 1│ PILLAR 2│ PILLAR 3│ PILLAR 4│ PILLAR 5│   PILLAR 0    │
│Afro-Pay │Sentinel │ Agent   │NetraID  │TrustNode│  Agentic Fuel │
│(Remit)  │ (SOC)   │ Cloud   │(ID)     │ (AI)    │  (Billing)    │
├─────────┴─────────┴─────────┴─────────┴─────────┴───────────────┤
│                     CELERY WORKERS                               │
│         metering, billing, topup, fraud detection                │
├─────────────────────────────────────────────────────────────────┤
│   PostgreSQL    │    Redis    │  Paystack/Flutterwave/Stripe     │
│  (16 tables)    │  (cache)    │  (payment integrations)          │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, Celery, Redis
- **Database:** PostgreSQL 16 with 16 tables
- **Frontend:** React 18, Tailwind CSS, Vite
- **Infrastructure:** Kubernetes, Terraform, Docker
- **Deployment:** AWS Cape Town (Africa), AWS Frankfurt (Europe)
- **Security:** Zero-Trust, OWASP Top 10 compliance

## Quick Start

```bash
# Clone and install
git clone <repo>
cd dutchkem-fortress-suite

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Start services
docker-compose up -d

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
dutchkem-fortress-suite/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/    # 7 API routers
│   │   ├── core/              # Config, DB, security
│   │   ├── integrations/      # Paystack, Flutterwave, Stripe
│   │   ├── models/            # 16 SQLAlchemy models
│   │   ├── services/          # Billing, metering, FX
│   │   └── workers/           # Celery tasks
│   └── alembic/               # DB migrations
├── frontend/
│   └── src/
│       ├── components/        # Layout, shared components
│       ├── pages/             # Dashboard, Wallet, Agents, etc.
│       └── lib/               # API client
├── k8s/                       # Kubernetes manifests
│   ├── base/                  # Core deployments
│   └── overlays/              # Africa + Europe regions
├── infra/terraform/           # AWS infrastructure
└── docs/                      # Investor deck, guides
```

## Pillars

| # | Name | Description | Revenue Model |
|---|------|-------------|---------------|
| 0 | Agentic Fuel | Credit billing engine (1 Credit = $0.10 USD) | Platform-wide metering |
| 1 | Afro-Pay | Web3 remittance & fintech | 0.5% settlement fee |
| 2 | Sentinel Africa | SOC-as-a-Service | $500/mo per threat |
| 3 | Agent Cloud | Vertical AI workforce | $1.50–$2.00/task |
| 4 | NetraID | Digital identity & compliance | Per-verification fee |
| 5 | TrustNode | AI abstraction layer | Token-based metering |

## License

Proprietary — Dutchkem Ventures Ltd.
