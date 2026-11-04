#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KUBE_CONTEXT="${KUBE_CONTEXT:-kind-local-platform}"
API_URL="${QUANLYKHO_API_URL:-http://127.0.0.1:8000}"
WEB_URL="${QUANLYKHO_WEB_URL:-http://127.0.0.1:8080}"
K=(kubectl --context "$KUBE_CONTEXT")

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$1" >&2
    exit 1
  }
}

http_status() {
  curl --silent --show-error --output /dev/null --max-time 5 \
    --write-out '%{http_code}' "$1"
}

require_command kubectl
require_command curl
require_command node
require_command python3

printf '%s\n' '=== Local interview demo: verified state only ==='
printf 'Kubernetes context: %s\n' "$KUBE_CONTEXT"

"${K[@]}" cluster-info >/dev/null
"${K[@]}" wait --for=condition=Ready nodes --all --timeout=30s >/dev/null
printf '\n--- kind nodes ---\n'
"${K[@]}" get nodes -o wide

"${K[@]}" wait --for=condition=Ready pods --all -n argocd --timeout=60s >/dev/null
printf '\n--- Argo CD control plane ---\n'
"${K[@]}" -n argocd get pods

printf '\n--- GitOps configuration and current application status ---\n'
"${K[@]}" -n argocd get appprojects,applications
"${K[@]}" -n argocd get application quanlykho \
  -o 'custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,SOURCE:.spec.source.targetRevision'
workloads="$("${K[@]}" -n quanlykho get deployments,statefulsets,services --no-headers)"
printf 'QuanLyKho namespace workloads: '
if [[ -z "$workloads" ]]; then
  printf 'none\n'
else
  printf '\n%s\n' "$workloads"
fi

printf '\n--- Local QuanLyKho endpoints ---\n'
api_status="$(http_status "$API_URL/api/v1/health/ready")"
web_status="$(http_status "$WEB_URL/")"
printf 'API readiness: HTTP %s (%s/api/v1/health/ready)\n' "$api_status" "$API_URL"
printf 'Web UI:        HTTP %s (%s/)\n' "$web_status" "$WEB_URL"
[[ "$api_status" == 200 ]] || { printf 'API readiness check failed\n' >&2; exit 1; }
[[ "$web_status" == 200 ]] || { printf 'Web UI check failed\n' >&2; exit 1; }

printf '\n--- Platform-owned SRE demo API unit tests ---\n'
(cd "$ROOT/app/sre-demo-api" && npm test)

printf '\n--- Platform gate regression tests ---\n'
(cd "$ROOT" && python3 tests/test_gates.py)

printf '\n--- Manifest composition checks ---\n'
(
  cd "$ROOT"
  kubectl kustomize platform/envoy-gateway/gateway >/dev/null
  kubectl kustomize platform/envoy-gateway/proof-backend >/dev/null
  kubectl kustomize deploy/overlays/validation >/dev/null
)
printf 'Gateway, proof-backend, and validation Kustomize roots rendered successfully.\n'

printf '\n%s\n' \
  'Demo checks passed. QuanLyKho remains manually promoted and unsynced in kind.' \
  'This runner is read-only: it does not apply manifests, sync Argo CD, register users, or mutate Azure.'
