#!/bin/bash
set -euo pipefail

# Dutchkem Fortress — Production Deployment Script
# Run this from the repo root

REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
CLUSTER="fortress-africa"
NAMESPACE="dutchkem"
API_IMAGE="${REGISTRY}/dutchkem-fortress-api"
ADMIN_IMAGE="${REGISTRY}/dutchkem-fortress-admin"

echo "=== Dutchkem Fortress — Production Deploy ==="
echo "Cluster: ${CLUSTER}"
echo "Namespace: ${NAMESPACE}"
echo ""

# Step 1: Configure AWS
echo "[1/6] Configuring AWS credentials..."
aws eks update-kubeconfig --name "${CLUSTER}" --region "${AWS_REGION}"

# Step 2: Create namespace
echo "[2/6] Ensuring namespace exists..."
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Apply secrets
echo "[3/6] Applying secrets..."
kubectl apply -f k8s/base/secrets.yaml -n "${NAMESPACE}"

# Step 4: Run migrations
echo "[4/6] Running database migrations..."
kubectl run fortress-migrate --rm -i --restart=Never \
  --image="${API_IMAGE}:latest" \
  --env="DATABASE_URL=${DATABASE_URL}" \
  --command -- alembic upgrade head

# Step 5: Deploy
echo "[5/6] Applying Kubernetes manifests..."
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/database.yaml -n "${NAMESPACE}"
kubectl apply -f k8s/base/api-deployment.yaml -n "${NAMESPACE}"
kubectl apply -f k8s/base/celery-deployment.yaml -n "${NAMESPACE}"
kubectl apply -f k8s/base/frontend-deployment.yaml -n "${NAMESPACE}"
kubectl apply -f k8s/base/hpa.yaml -n "${NAMESPACE}"

# Step 6: Verify
echo "[6/6] Verifying deployment..."
kubectl rollout status deployment/fortress-api -n "${NAMESPACE}" --timeout=300s
kubectl rollout status deployment/fortress-celery-worker -n "${NAMESPACE}" --timeout=300s
kubectl rollout status deployment/fortress-admin -n "${NAMESPACE}" --timeout=300s

echo ""
echo "=== Deployment Complete ==="
kubectl get pods -n "${NAMESPACE}"
echo ""
echo "API endpoint: https://api.dutchkem.com"
echo "Admin dashboard: https://admin.dutchkem.com"
