#!/usr/bin/env bash
# Sync an ArgoCD application to a revision and wait until healthy.
#
# Credentials come from the environment — NEVER hardcode them in this file.
# Copy scripts/.env.example to scripts/.env, fill values, then:
#   source scripts/.env && ./scripts/sync-argocd.sh
#
# TLS is verified by default. Only set ARGOCD_INSECURE=true for
# self-signed dev clusters — never for production.
set -Eeuo pipefail

APP_NAME="${APP_NAME:-aks-sre-platform}"
REVISION="${REVISION:-main}"
ARGOCD_SERVER="${ARGOCD_SERVER:?Set ARGOCD_SERVER (host, no scheme)}"
ARGOCD_USERNAME="${ARGOCD_USERNAME:?Set ARGOCD_USERNAME}"
ARGOCD_PASSWORD="${ARGOCD_PASSWORD:?Set ARGOCD_PASSWORD}"
ARGOCD_INSECURE="${ARGOCD_INSECURE:-false}"
SYNC_TIMEOUT="${SYNC_TIMEOUT:-600}"

login_args=( login "$ARGOCD_SERVER" --username "$ARGOCD_USERNAME" --password "$ARGOCD_PASSWORD" )
if [[ "$ARGOCD_INSECURE" == "true" ]]; then
  echo "!! WARN: ARGOCD_INSECURE=true — TLS verification DISABLED. Dev use only." >&2
  login_args+=( --insecure )
fi

echo "==> Logging in to ArgoCD at ${ARGOCD_SERVER}"
argocd "${login_args[@]}"

echo "==> Checking app '${APP_NAME}' exists"
argocd app get "$APP_NAME" >/dev/null 2>&1 || {
  echo "App '${APP_NAME}' not found in ArgoCD" >&2
  exit 1
}

echo "==> Keeping sync automated: setting target revision to ${REVISION}"
# app set only changes the revision pin; it does NOT disable auto-sync policy
argocd app set "$APP_NAME" --revision "$REVISION"

echo "==> Syncing (one-shot mode, retries on transient errors)"
if argocd app get "$APP_NAME" -o json | grep -q '"automatedSyncPolicy"'; then
  echo "    Note: app has an automated sync policy; manual sync may conflict." >&2
fi
argocd app sync "$APP_NAME" --server-side --retry-limit 5

echo "==> Waiting for healthy (timeout ${SYNC_TIMEOUT}s)"
argocd app wait "$APP_NAME" --health --timeout "$SYNC_TIMEOUT"

echo "==> Final status"
argocd app status "$APP_NAME"

echo "DONE: ${APP_NAME} synced to ${REVISION}."
