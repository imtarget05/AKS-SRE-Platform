#!/usr/bin/env bash
# Trigger a Cloudflare Pages deployment via API.
#
# NOTE: this only works for DIRECT-UPLOAD Pages projects.
# Git-connected Pages/Workers projects do not accept API deployment
# creation — push a commit / re-run the CI pipeline instead.
set -Eeuo pipefail

CLOUDFLARE_API_TOKEN="${CLOUDFLARE_API_TOKEN:?Set CLOUDFLARE_API_TOKEN in scripts/.env}"
CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:?Set CLOUDFLARE_ACCOUNT_ID in scripts/.env}"
CLOUDFLARE_PROJECT_NAME="${CLOUDFLARE_PROJECT_NAME:?Set CLOUDFLARE_PROJECT_NAME in scripts/.env}"

echo "==> Creating deployment for project '${CLOUDFLARE_PROJECT_NAME}'"
body="$(mktemp)"
http_code="$(curl -sS -o "$body" -w '%{http_code}' \
  -X POST "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/pages/projects/${CLOUDFLARE_PROJECT_NAME}/deployments" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json")"

python3 - "$body" "$http_code" <<'PY'
import json,sys
body_path, code = sys.argv[1], sys.argv[2]
try:
    d=json.load(open(body_path))
except Exception:
    print(f"FAIL: HTTP {code}, non-JSON response"); sys.exit(1)
ok = d.get("success") and str(code).startswith("2")
if ok:
    dep=(d.get("result") or {})
    print("OK: deployment created")
    print("  id:     ", dep.get("id"))
    print("  url:    ", (dep.get("url") or "")[:80])
else:
    print(f"FAIL: HTTP {code}")
    for e in (d.get("errors") or []):
        print("  error", e.get("code"), e.get("message"))
    sys.exit(1)
PY
rm -f "$body"

echo "==> Validate the deployed URL responds 200 before considering it done."
