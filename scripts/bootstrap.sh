#!/usr/bin/env bash
# Bootstrap the maintained platform components on an already-provisioned cluster.
#
# Scope is defined by MANIFEST-INVENTORY.md, not by history:
#   1. Argo CD  — upstream install manifest (no chart owned by this repo),
#                 pinned by platform/argocd/VERSION and applied SERVER-SIDE.
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
VERSION_FILE="$ROOT/platform/argocd/VERSION"
REPO_URL="${REPO_URL:-}"
APPLY_LEGACYAPP="${APPLY_LEGACYAPP:-0}"

require_file() {
  [ -f "$1" ] || { echo "FATAL: missing required file: $1" >&2; exit 1; }
}

# Fail before touching the cluster, not after installing half of it.
require_file "$ROOT/platform/argocd/appproject.yaml"
require_file "$VERSION_FILE"
[ -d "$APPS_DIR" ] || { echo "FATAL: missing $APPS_DIR" >&2; exit 1; }
require_file "$APPS_DIR/flashsale.yaml"
require_file "$APPS_DIR/legacyapp.yaml"

# The Argo CD version is pinned in exactly ONE place: platform/argocd/VERSION.
# Before this, the script installed from the floating `stable` branch while the
# README, the ADR and the evidence doc all claimed a pinned v3.5.3 — so the
# documented version and the installed version were different facts (the
# floating branch had already moved to v3.5.5). Reading the tag from one file
# is what makes "what we install" and "what we document" the same statement.
ARGOCD_VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
case "$ARGOCD_VERSION" in
  v[0-9]*.[0-9]*.[0-9]*) ;;
  *)
    echo "FATAL: $VERSION_FILE must hold a vMAJOR.MINOR.PATCH tag, got '$ARGOCD_VERSION'" >&2
    exit 1
    ;;
esac
ARGOCD_MANIFEST_URL="https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"

echo "==> 1/3 Installing Argo CD ${ARGOCD_VERSION} (pinned)"
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
# SERVER-SIDE APPLY IS REQUIRED HERE, NOT A STYLE CHOICE.
#
# Measured on a clean kind cluster on 2026-10-20 with the pinned v3.5.5
# manifest:
#
#   client-side apply ->
#     The CustomResourceDefinition "applicationsets.argoproj.io" is invalid:
#     metadata.annotations: Too long: may not be more than 262144 bytes
#     exit code 1
#
# and the consequence is not cosmetic: the `applicationsets.argoproj.io` CRD is
# never created, the ApplicationSet controller crashes on start, and the
# `&&` chain aborts the remaining install. The cause is structural — a
# client-side apply stores the ENTIRE object in the
# kubectl.kubernetes.io/last-applied-configuration annotation, and the
# ApplicationSet CRD schema is larger than the 256 KiB annotation limit. A
# server-side apply keeps the object server-side and never writes that
# annotation.
#
# The whole upstream manifest is applied server-side: on the same clean
# cluster every object (3 CRDs, StatefulSet, Deployments, Services, RBAC,
# ConfigMaps, NetworkPolicies) applied with rc=0, so nothing had to fall back
# to client-side apply. `--force-conflicts` is required because a re-run takes
# ownership from the previous field manager.
kubectl apply -n argocd --server-side --force-conflicts \
  --field-manager=aks-sre-bootstrap \
  -f "$ARGOCD_MANIFEST_URL"
kubectl -n argocd rollout status deploy/argocd-server --timeout=300s

# Assert the running control plane IS the pinned version. A drifted install is
# a silent reproducibility failure, and this is the last point at which it can
# still be stopped instead of documented around.
INSTALLED_IMAGE="$(kubectl -n argocd get deploy argocd-server \
  -o jsonpath='{.spec.template.spec.containers[0].image}')"
case "$INSTALLED_IMAGE" in
  *":${ARGOCD_VERSION}"|*":${ARGOCD_VERSION}@sha256:"*)
    echo "    argocd-server image: $INSTALLED_IMAGE (matches the pin)" ;;
  *)
    echo "FATAL: argocd-server runs '$INSTALLED_IMAGE' but the pin is '$ARGOCD_VERSION'" >&2
    exit 1 ;;
esac

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
# These repo-owned objects are applied CLIENT-SIDE on purpose. They are orders
# of magnitude below the 256 KiB annotation limit that breaks the upstream
# CRDs, and client-side apply computes a diff against the previously applied
# configuration: a key removed from a manifest in Git is removed from the
# cluster too. A server-side apply only removes fields that the applying
# field manager owns, so a field owned by Argo CD or by an earlier operator
# survives — a weaker contract for the one object whose entire purpose is to
# BE the allowlist.
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
