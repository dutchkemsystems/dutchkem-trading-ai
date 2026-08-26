#!/bin/bash
set -euo pipefail

# Dutchkem Fortress — Database Setup
# Run after infrastructure is provisioned

echo "=== Dutchkem Fortress — Database Setup ==="

# Step 1: Run migrations
echo "[1/2] Running Alembic migrations..."
kubectl run fortress-migrate --rm -i --restart=Never \
  --image=$(kubectl get deployment fortress-api -n dutchkem -o jsonpath='{.spec.template.spec.containers[0].image}') \
  --env-from=secret-ref=fortress-secrets \
  --command -- alembic upgrade head

# Step 2: Seed agents
echo "[2/2] Seeding agent registry..."
kubectl run fortress-seed --rm -i --restart=Never \
  --image=$(kubectl get deployment fortress-api -n dutchkem -o jsonpath='{.spec.template.spec.containers[0].image}') \
  --env-from=secret-ref=fortress-secrets \
  --command -- python -c "
from app.core.database import engine, Base
from app.models import *
from sqlalchemy import text

async def seed():
    async with engine.begin() as conn:
        # Seed agents
        agents = [
            ('KYC Agent', 'kyc-agent', 'netra_id', 2.0, 'Identity verification agent'),
            ('Sentinel Recon', 'sentinel-recon', 'sentinel', 500, 'Network reconnaissance agent'),
            ('Sales Agent', 'sales-agent', 'agent_cloud', 1.5, 'Sales automation agent'),
            ('Remittance Router', 'afropay-router', 'afro_pay', 0.5, 'Cross-border payment routing'),
            ('TrustNode Router', 'trustnode-router', 'trust_node', 0.01, 'AI model routing'),
            ('Loan Recovery', 'loan-recovery', 'agent_cloud', 1.5, 'Loan recovery agent'),
            ('Deepfake Detection', 'deepfake-detect', 'sentinel', 500, 'Deepfake detection agent'),
            ('Phishing Takedown', 'phishing-takedown', 'sentinel', 500, 'Phishing takedown agent'),
        ]
        for name, slug, pillar, cost, desc in agents:
            await conn.execute(text(
                'INSERT INTO agents (name, slug, pillar, credit_cost_per_task, description, is_active) '
                'VALUES (:name, :slug, :pillar, :cost, :desc, true) '
                'ON CONFLICT (slug) DO NOTHING'
            ), {'name': name, 'slug': slug, 'pillar': pillar, 'cost': cost, 'desc': desc})

import asyncio
asyncio.run(seed())
print('Agents seeded successfully')
"

echo ""
echo "=== Database Setup Complete ==="
