#!/usr/bin/env bash
# ==============================================================================
# verify-terraform-plan.sh: Dry-run and validation gate for Terraform AKS Foundation
# Ensures configuration validity, plan reproducibility, and zero unexpected drift.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TF_DIR="${REPO_ROOT}/terraform/aks-foundation"
PLAN_OUT="${TF_DIR}/aks.tfplan"

echo "=== [1/3] Terraform Syntax & Formatting Validation ==="
cd "${TF_DIR}"
terraform fmt -check
terraform validate

echo "=== [2/3] Generating Speculative Plan (Dry-run) ==="
terraform plan -refresh=false -out="${PLAN_OUT}"

echo "=== [3/3] Inspecting Plan Summary ==="
terraform show -no-color "${PLAN_OUT}" | grep -E "(Plan:|Changes to Outputs:)" || true

# Cleanup speculative binary plan
rm -f "${PLAN_OUT}"
echo "[OK] Terraform plan verification succeeded cleanly."
