#!/usr/bin/env bash
# Local AKS plan helper. Cloud mutation uses the protected AKS Deploy workflow.
# Usage: ./scripts/rebuild-aks.sh [plan]

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
    echo "Apply requires the reviewed AKS Deploy workflow's protected production gate." >&2
    exit 2
    ;;
  destroy)
    echo "Destruction requires the reviewed AKS Deploy workflow's protected production gate." >&2
    exit 2
    ;;
  *)
    echo "Usage: $0 [plan]"
    exit 1
    ;;
esac
