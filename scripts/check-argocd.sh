#!/usr/bin/env bash
# Read-only health check for an ArgoCD application.
# Usage: source scripts/.env && ./scripts/check-argocd.sh
set -Eeuo pipefail

APP_NAME="${APP_NAME:-aks-sre-platform}"
ARGOCD_SERVER="${ARGOCD_SERVER:?Set ARGOCD_SERVER}"
ARGOCD_USERNAME="${ARGOCD_USERNAME:?Set ARGOCD_USERNAME}"
ARGOCD_PASSWORD="${ARGOCD_PASSWORD:?Set ARGOCD_PASSWORD}"
ARGOCD_INSECURE="${ARGOCD_INSECURE:-false}"

login_args=( login "$ARGOCD_SERVER" --username "$ARGOCD_USERNAME" --password "$ARGOCD_PASSWORD" )
if [[ "$ARGOCD_INSECURE" == "true" ]]; then
  echo "!! WARN: TLS verification disabled" >&2
  login_args+=( --insecure )
fi

argocd "${login_args[@]}"

echo "==> App details (wide)"
argocd app get "$APP_NAME" -o wide

echo "==> Status"
argocd app status "$APP_NAME"

echo "==> Resources not healthy/synced (empty means all good)"
argocd app get "$APP_NAME" -o json \
  | python3 -c '
import json,sys
app=json.load(sys.stdin)
bad=[r for s in (app.get("status",{}).get("resources") or [])
     if s.get("health",{}).get("status") not in (None,"Healthy")
     or s.get("status") not in (None,"Synced")]
for r in bad or []:
    print(r.get("kind"), r.get("namespace",""), r.get("name"),
          r.get("health",{}).get("status"), r.get("status"))
sys.exit(1 if bad else 0)'
