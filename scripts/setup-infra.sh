#!/bin/bash
set -euo pipefail

# Dutchkem Fortress — Infrastructure Provisioning
# Run once to set up AWS infrastructure

echo "=== Dutchkem Fortress — Infrastructure Setup ==="

# Step 1: Terraform init
echo "[1/4] Initializing Terraform..."
cd infra/terraform
terraform init

# Step 2: Plan
echo "[2/4] Planning infrastructure..."
terraform plan -out=tfplan

# Step 3: Apply
echo "[3/4] Applying infrastructure..."
terraform apply tfplan

# Step 4: Configure kubectl
echo "[4/4] Configuring kubectl..."
CLUSTER_NAME=$(terraform output -raw africa_cluster_name)
AWS_REGION=$(terraform output -raw primary_region 2>/dev/null || echo "af-south-1")
aws eks update-kubeconfig --name "${CLUSTER_NAME}" --region "${AWS_REGION}"

echo ""
echo "=== Infrastructure Ready ==="
echo "Run ./scripts/deploy.sh to deploy the application"
