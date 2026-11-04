#!/usr/bin/env bash
# Bootstrap the maintained platform components on an already-provisioned cluster.
#
# Scope is defined by MANIFEST-INVENTORY.md, not by history:
#   1. Argo CD  — upstream install manifest (no chart owned by this repo),
#                 pinned by platform/argocd/VERSION and applied SERVER-SIDE.
#   2. KEDA     — optional upstream chart, enabled only when INSTALL_KEDA=1.
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
#   scripts/bootstrap.sh                 # local Argo CD + maintained Applications
#   INSTALL_KEDA=1 scripts/bootstrap.sh  # install KEDA explicitly
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPS_DIR="$ROOT/platform/argocd/applications"
VERSION_FILE="$ROOT/platform/argocd/VERSION"
KUBE_CONTEXT="${KUBE_CONTEXT:-kind-local-platform}"
INSTALL_KEDA="${INSTALL_KEDA:-0}"
kubectl_ctx() {
  kubectl --context "$KUBE_CONTEXT" "$@"
}

require_file() {
  [ -f "$1" ] || { echo "FATAL: missing required file: $1" >&2; exit 1; }
}

# Fail before touching the cluster, not after installing half of it.
require_file "$ROOT/platform/argocd/appproject.yaml"
require_file "$VERSION_FILE"
[ -d "$APPS_DIR" ] || { echo "FATAL: missing $APPS_DIR" >&2; exit 1; }
require_file "$APPS_DIR/creditflow.yaml"
require_file "$APPS_DIR/quanlykho.yaml"
case "$INSTALL_KEDA" in
  0|1) ;;
  *) echo "FATAL: INSTALL_KEDA must be 0 or 1, got '$INSTALL_KEDA'" >&2; exit 1 ;;
esac

# Fail closed on the explicitly selected context before the first mutation.
kubectl_ctx cluster-info >/dev/null

# Fail-closed context guard: refuse to mutate any cluster that is not kind-local-platform.
ACTIVE_CONTEXT="$(kubectl config current-context 2>/dev/null || true)"
if [ "${ACTIVE_CONTEXT}" != "${KUBE_CONTEXT}" ]; then
  echo "::error::kubectl current-context is '${ACTIVE_CONTEXT}', expected '${KUBE_CONTEXT}' (kind-local-platform)." >&2
  echo "::error::Refusing to mutate a non-kind-local-platform cluster. Run: kubectl config use-context ${KUBE_CONTEXT}" >&2
  exit 1
fi
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

echo "==> 1/3 Installing Argo CD ${ARGOCD_VERSION} (pinned) on ${KUBE_CONTEXT}"
kubectl_ctx create namespace argocd --dry-run=client -o yaml \
  | kubectl_ctx apply -f -
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
kubectl_ctx apply -n argocd --server-side --force-conflicts \
  --field-manager=aks-sre-bootstrap \
  -f "$ARGOCD_MANIFEST_URL"
kubectl_ctx -n argocd rollout status deploy/argocd-server --timeout=300s

# Assert the running control plane IS the pinned version. A drifted install is
# a silent reproducibility failure, and this is the last point at which it can
# still be stopped instead of documented around.
INSTALLED_IMAGE="$(kubectl_ctx -n argocd get deploy argocd-server \
  -o jsonpath='{.spec.template.spec.containers[0].image}')"
case "$INSTALLED_IMAGE" in
  *":${ARGOCD_VERSION}"|*":${ARGOCD_VERSION}@sha256:"*)
    echo "    argocd-server image: $INSTALLED_IMAGE (matches the pin)" ;;
  *)
    echo "FATAL: argocd-server runs '$INSTALLED_IMAGE' but the pin is '$ARGOCD_VERSION'" >&2
    exit 1 ;;
esac

if [ "$INSTALL_KEDA" = "1" ]; then
  echo "==> 2/3 Installing KEDA (upstream chart)"
  helm repo add kedacore https://kedacore.github.io/charts --force-update
  helm repo update
  helm upgrade --install keda kedacore/keda \
    --kube-context "$KUBE_CONTEXT" \
    --namespace keda --create-namespace \
    --set podIdentity.azureWorkloadIdentity.enabled=true \
    --set serviceAccount.create=true \
    --set serviceAccount.name=keda-operator
  echo "    note: no ScaledObject is applied here; install KEDA only when"
  echo "          the owning workload and identity have been reviewed."
else
  echo "==> 2/3 Skipping optional KEDA install (set INSTALL_KEDA=1 to enable)"
fi

echo "==> 3/3 Applying AppProject and maintained Applications"
# These repo-owned objects are applied CLIENT-SIDE on purpose. They are orders
# of magnitude below the 256 KiB annotation limit that breaks the upstream
# CRDs, and client-side apply computes a diff against the previously applied
# configuration: a key removed from a manifest in Git is removed from the
# cluster too. A server-side apply only removes fields that the applying
# field manager owns, so a field owned by Argo CD or by an earlier operator
# survives — a weaker contract for the one object whose entire purpose is to
# BE the allowlist.
kubectl_ctx apply -f "$ROOT/platform/argocd/appproject.yaml"

for app in "$APPS_DIR"/*.yaml; do
  kubectl_ctx apply -f "$app"
done

echo "Done. Check: kubectl --context ${KUBE_CONTEXT} get applications -n argocd"
