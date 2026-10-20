#!/usr/bin/env bash
# Bootstrap the maintained platform components on an already-provisioned cluster.
#
# Scope is defined by MANIFEST-INVENTORY.md, not by history:
#   1. Argo CD  — upstream install manifest (no chart owned by this repo).
#   2. KEDA     — upstream chart, for the order worker that FlashSale-Backend owns.
#   3. AppProject + maintained Applications from platform/argocd/applications/.
#
# Deliberately NOT applied (superseded by MANIFEST-INVENTORY.md):
#   - kubernetes/keda-trigger-auth.yaml     LEGACY_NOT_DEPLOYED (Secret absent)
#   - kubernetes/keda-autoscaler.yaml       LEGACY_NOT_DEPLOYED (contradicts the
#                                           Service Bus connection in order-worker)
#   - kubernetes/order-worker.yaml          EXTERNAL_WORKLOAD_REFERENCE (P01 owns it)
#   - kubernetes/pod-disruption-budget.yaml SUPERSEDED (selector matches nothing)
# Applying them was the previous behaviour of this script; it produced objects
# that could never become ready and is why step 5/5 referenced a file that only
# exists as `.disabled`.
#
# This is not a CI step. A human runs it against a cluster that kubectl already
# points at. It creates no Azure resource and applies no Terraform.
#
# Usage:
#   scripts/bootstrap.sh
#   scripts/bootstrap.sh                 # KEDA identity is resolved by FlashSale-Backend
#   APPLY_LEGACYAPP=1 scripts/bootstrap.sh   # only after ADR-015 source switch approval
#   REPO_URL=https://... scripts/bootstrap.sh  # override the FlashSale source URL
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPS_DIR="$ROOT/platform/argocd/applications"
REPO_URL="${REPO_URL:-}"
APPLY_LEGACYAPP="${APPLY_LEGACYAPP:-0}"

require_file() {
  [ -f "$1" ] || { echo "FATAL: missing required file: $1" >&2; exit 1; }
}

# Fail before touching the cluster, not after installing half of it.
require_file "$ROOT/platform/argocd/appproject.yaml"
[ -d "$APPS_DIR" ] || { echo "FATAL: missing $APPS_DIR" >&2; exit 1; }
require_file "$APPS_DIR/flashsale.yaml"
require_file "$APPS_DIR/legacyapp.yaml"

echo "==> 1/3 Installing Argo CD"
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server --timeout=300s

echo "==> 2/3 Installing KEDA (upstream chart)"
helm repo add kedacore https://kedacore.github.io/charts 2>/dev/null || true
helm repo update
helm upgrade --install keda kedacore/keda \
  --namespace keda --create-namespace \
  --set podIdentity.azureWorkloadIdentity.enabled=true \
  --set serviceAccount.create=true \
  --set serviceAccount.name=keda-operator
echo "    note: no ScaledObject is applied here. Autoscaling of the order worker"
echo "          is owned by FlashSale-Backend; the local KEDA manifests are"
echo "          LEGACY_NOT_DEPLOYED and would target a workload this repo does"
echo "          not own."

echo "==> 3/3 Applying AppProject and maintained Applications"
kubectl apply -f "$ROOT/platform/argocd/appproject.yaml"

for app in "$APPS_DIR"/*.yaml; do
  name="$(basename "$app")"
  if [ "$name" = "legacyapp.yaml" ] && [ "$APPLY_LEGACYAPP" != "1" ]; then
    echo "    skipping legacyapp.yaml — ADR-015 source switch is not approved."
    echo "    Re-run with APPLY_LEGACYAPP=1 after the reviewed GitOps change."
    continue
  fi
  if [ -n "$REPO_URL" ] && grep -q 'repoURL: https://github.com/imtarget05/FlashSale-Backend.git' "$app"; then
    sed "s|https://github.com/imtarget05/FlashSale-Backend.git|${REPO_URL}|g" "$app" | kubectl apply -f -
  else
    kubectl apply -f "$app"
  fi
done

echo "Done. Check: kubectl get applications -n argocd"
