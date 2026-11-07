#!/usr/bin/env bash
# Trigger a Render deploy via its deploy-hook URL.
#
# SECURITY: the deploy-hook URL IS a credential (one POST = prod deploy).
# Keep it in scripts/.env, never in git, never echo it, never paste to chat.
set -Eeuo pipefail

RENDER_DEPLOY_HOOK="${RENDER_DEPLOY_HOOK:?Set RENDER_DEPLOY_HOOK in scripts/.env (treated as a secret)}"

echo "==> Triggering Render deploy (hook URL is secret, not printed)"
body="$(mktemp)"
http_code="$(curl -sS -o "$body" -w '%{http_code}' -X POST "$RENDER_DEPLOY_HOOK")"

if [[ "$http_code" == "2"* ]]; then
  echo "OK: deploy accepted (HTTP ${http_code})"
  python3 - "$body" <<'PY'
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print("deploy id:", d.get("id"))
    print("status:   ", d.get("status"))
    print("trigger:  ", d.get("trigger"))
except Exception:
    pass
PY
  echo "==> Follow logs: https://dashboard.render.com (or: render-cli logs --follow)"
else
  echo "FAIL: HTTP ${http_code}" >&2
  cat "$body" >&2
  rm -f "$body"
  exit 1
fi
rm -f "$body"

echo
echo "VERIFY after deploy (see docs/RUNBOOK-DEPLOY-12-STEP.md):"
echo "  - no 'UnknownHostException' in logs"
echo "  - no CrashLoopBackOff"
echo "  - app health endpoint returns 200"
