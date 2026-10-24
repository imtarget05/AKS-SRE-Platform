#!/usr/bin/env bash
# Rebuild AKS cluster + Argo CD bootstrap
# Usage: ./scripts/rebuild-aks.sh [plan|apply|destroy]

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ACTION="${1:-plan}"
TERRAFORM_DIR="${ROOT}/terraform"

cd "$TERRAFORM_DIR"

case "$ACTION" in
  plan)
    echo "🔍 Running terraform plan..."
    terraform fmt -recursive
    terraform init -upgrade
    terraform plan -out=tfplan
    ;;
  apply)
    echo "🚀 Running terraform apply..."
    if [[ ! -f tfplan ]]; then
      echo "❌ No tfplan found. Run 'plan' first."
      exit 1
    fi
    terraform apply tfplan
    echo "✅ AKS cluster created. Bootstrapping Argo CD..."
    # Get AKS credentials
    RESOURCE_GROUP=$(terraform output -raw resource_group_name)
    CLUSTER_NAME=$(terraform output -raw aks_cluster_name)
    az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --overwrite-existing
    # Bootstrap Argo CD
    cd "$ROOT"
    ./scripts/bootstrap.sh
    echo "✅ Argo CD bootstrapped. Verifying..."
    kubectl get applications -n argocd
    ;;
  destroy)
    echo "💥 Destroying AKS cluster..."
    terraform destroy -auto-approve
    ;;
  *)
    echo "Usage: $0 [plan|apply|destroy]"
    exit 1
    ;;
esac
