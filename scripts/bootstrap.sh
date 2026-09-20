#!/usr/bin/env bash
# Bootstrap AKS platform: ArgoCD (GitOps) + KEDA (event-driven autoscaling),
# sau đó đăng ký Application flash-sale-app.
# Yêu cầu: kubectl đã trỏ vào AKS (xem output `kube_config_command` của Terraform).
set -euo pipefail

KEDA_IDENTITY_CLIENT_ID="${1:-<keda_identity_client_id>}"
REPO_URL="${REPO_URL:-https://github.com/imtarget05/FlashSale-Backend.git}"
APP_PATH="infrastructure/kubernetes/overlays/prod"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> 1/5 Installing ArgoCD"
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

echo "==> Waiting for ArgoCD server..."
kubectl -n argocd rollout status deploy/argocd-server --timeout=180s

echo "==> 2/5 Installing KEDA via Helm"
helm repo add kedacore https://kedacore.github.io/charts 2>/dev/null || true
helm repo update
helm upgrade --install keda kedacore/keda \
  --namespace keda --create-namespace \
  --set podIdentity.azureWorkloadIdentity.enabled=true \
  --set serviceAccount.create=true \
  --set serviceAccount.name=keda-operator

echo "==> 3/5 Applying KEDA TriggerAuthentication (workload identity: $KEDA_IDENTITY_CLIENT_ID)"
kubectl apply -f <(sed "s|<keda_identity_client_id>|${KEDA_IDENTITY_CLIENT_ID}|g" "$ROOT/kubernetes/keda-trigger-auth.yaml")

echo "==> 4/5 Applying KEDA ScaledObject + worker + PDB"
kubectl apply -f "$ROOT/kubernetes/keda-autoscaler.yaml"
kubectl apply -f "$ROOT/kubernetes/order-worker.yaml"
kubectl apply -f "$ROOT/kubernetes/pod-disruption-budget.yaml"

echo "==> 5/5 Registering ArgoCD Application ($REPO_URL::$APP_PATH)"
kubectl apply -f <(sed "s|https://github.com/imtarget05/Harness-of-Target.git|${REPO_URL}|g" "$ROOT/gitops/argocd/application.yaml")

echo "Done. Check: kubectl get applications -n argocd"
