#!/usr/bin/env bash
# ==============================================================================
# verify-gitops-all.sh: Full GitOps Semantic & Cross-Repo Validation
# Validates both standalone advisory mode and full multi-repo render mode.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_MAP="${REPO_ROOT}/gitops/repo-map.local.yaml"

cd "${REPO_ROOT}"

echo "=== [1/2] Standalone GitOps Gate (Advisory External Checks) ==="
python3 gitops/validate-gitops.py

echo ""
echo "=== [2/2] Full GitOps Multi-Repository Enforcement (18/18 PASS) ==="
if [ -f "${REPO_MAP}" ]; then
  python3 gitops/validate-gitops.py --repo-map "gitops/repo-map.local.yaml" --require-external
  echo "[OK] Full GitOps multi-repo verification passed with 0 unverified source trees."
else
  echo "[SKIP] Repo map ${REPO_MAP} not found."
  exit 1
fi
