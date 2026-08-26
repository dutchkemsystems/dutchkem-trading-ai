# Production Deployment Guide

## Prerequisites

1. **AWS Account** with ECR, EKS, RDS, ElastiCache access
2. **Domain names** pointed to your load balancer:
   - `api.dutchkem.com` → Backend API
   - `admin.dutchkem.com` → Admin Dashboard
3. **Payment provider accounts** with live API keys:
   - Paystack (Nigeria/NGN)
   - Flutterwave (Africa-wide)
   - Stripe (International USD)
4. **ExchangeRate API key** from exchangerate-api.com

## Step 1: Configure Secrets

```bash
# Copy and fill in production env
cp .env.production .env
# Edit .env with real values
```

## Step 2: Provision Infrastructure

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
export AWS_REGION=af-south-1

# Run infrastructure setup
chmod +x scripts/setup-infra.sh
./scripts/setup-infra.sh
```

This creates:
- EKS cluster in Cape Town (af-south-1)
- RDS PostgreSQL 16 (Multi-AZ)
- ElastiCache Redis 7
- VPC with public/private subnets

## Step 3: Setup Database

```bash
chmod +x scripts/setup-db.sh
./scripts/setup-db.sh
```

This runs Alembic migrations and seeds the agent registry.

## Step 4: Deploy Application

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

This deploys:
- FastAPI backend (3 replicas, HPA 3-20)
- Celery workers (2 replicas, HPA 2-10)
- Celery beat (1 replica)
- React admin dashboard (2 replicas)
- PostgreSQL + Redis (StatefulSets)

## Step 5: Configure DNS

Point your domains to the AWS Load Balancer:

```
api.dutchkem.com     → ALB DNS name
admin.dutchkem.com   → ALB DNS name
```

## Step 6: SSL Certificates

Cert-manager automatically provisions SSL certificates via Let's Encrypt.

## Step 7: Verify

```bash
# Check all pods
kubectl get pods -n dutchkem

# Check services
kubectl get svc -n dutchkem

# Check logs
kubectl logs -f deployment/fortress-api -n dutchkem

# Test API
curl https://api.dutchkem.com/health
```

## Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/fortress-api -n dutchkem
kubectl rollout undo deployment/fortress-celery-worker -n dutchkem
kubectl rollout undo deployment/fortress-admin -n dutchkem
```

## Monitoring

- **Grafana**: `kubectl port-forward svc/grafana 3000:3000 -n dutchkem`
- **Prometheus**: `kubectl port-forward svc/prometheus 9090:9090 -n dutchkem`
