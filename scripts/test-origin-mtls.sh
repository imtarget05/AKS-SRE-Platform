#!/usr/bin/env bash
# Live origin mTLS proof. A DNS outage or certificate validation error is not
# evidence that the Gateway rejected a client missing its mTLS certificate.
set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <origin-fqdn> <worker-health-url> <origin-ca-pem>" >&2
    exit 2
fi
ORIGIN_HOST="$1"
WORKER_URL="$2"
ORIGIN_CA_FILE="$3"
PROOF_KEY="${EDGE_PROOF_KEY:-}"
if [[ ! "$ORIGIN_HOST" =~ ^[A-Za-z0-9.-]+$ ]] ||
   [[ "$WORKER_URL" != https://*/flashsale/health/live ]] ||
   [[ ${#PROOF_KEY} -lt 32 ]] ||
   [[ ! -s "$ORIGIN_CA_FILE" ]]; then
    echo "Origin FQDN, exact HTTPS Worker health URL, origin CA, and EDGE_PROOF_KEY (>=32 bytes) are required." >&2
    exit 2
fi

NEG_LOG=$(mktemp)
POS_HEADERS=$(mktemp)
POS_BODY=$(mktemp)
trap 'rm -f "$NEG_LOG" "$POS_HEADERS" "$POS_BODY"' EXIT

echo "[TEST 1] Direct origin without a client certificate must fail at TLS."
set +e
NEG_CODE=$(curl --cacert "$ORIGIN_CA_FILE" -v -sS -o /dev/null -w '%{http_code}' \
    --connect-timeout 5 "https://${ORIGIN_HOST}/flashsale/health/live" 2>"$NEG_LOG")
NEG_RC=$?
set -e

if [[ "$NEG_CODE" != "000" ]] ||
   [[ "$NEG_RC" != "35" && "$NEG_RC" != "56" ]] ||
   ! grep -qi 'Connected to' "$NEG_LOG" ||
   ! grep -Eqi '(alert.*certificate|required.*certificate|certificate.*required)' "$NEG_LOG"; then
    echo "[FAIL] Origin did not prove certificate-required TLS rejection (curl rc=$NEG_RC, HTTP=$NEG_CODE)." >&2
    cat "$NEG_LOG" >&2
    exit 1
fi
echo "[PASS] Reachable origin rejected a missing client certificate at TLS."

echo "[TEST 2] Cloudflare Worker health path must reach the owner service."
NONCE=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
set +e
POS_CODE=$(curl -sS --fail-with-body -D "$POS_HEADERS" -o "$POS_BODY" -w '%{http_code}' \
    --connect-timeout 10 -H "X-Portfolio-Proof-Nonce: $NONCE" "$WORKER_URL")
POS_RC=$?
set -e
if [[ "$POS_RC" != "0" || "$POS_CODE" != "200" ]] ||
   ! grep -Eq '"status"[[:space:]]*:[[:space:]]*"healthy"' "$POS_BODY" ||
   ! grep -Eqi '^cache-control:[[:space:]]*private,[[:space:]]*no-store' "$POS_HEADERS"; then
    echo "[FAIL] Worker did not return the owner health response with no-store (curl rc=$POS_RC, HTTP=$POS_CODE)." >&2
    exit 1
fi
python3 - "$ORIGIN_HOST" "$NONCE" "$POS_HEADERS" "$POS_BODY" <<'PY'
import hashlib
import hmac
import os
import pathlib
import sys

origin, nonce, headers_path, body_path = sys.argv[1:]
headers = {}
for line in pathlib.Path(headers_path).read_text().splitlines():
    if ":" in line:
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
body = pathlib.Path(body_path).read_bytes()
message = f"{nonce}\n{origin}\n200\n{hashlib.sha256(body).hexdigest()}".encode()
expected = hmac.new(os.environ["EDGE_PROOF_KEY"].encode(), message, hashlib.sha256).hexdigest()
actual = headers.get("x-portfolio-origin-proof", "")
if (headers.get("x-portfolio-origin-target") != origin or
        headers.get("x-portfolio-proof-nonce") != nonce or
        not hmac.compare_digest(actual, expected)):
    raise SystemExit("[FAIL] Worker response lacks a valid fresh origin-binding proof.")
PY
echo "[PASS] Worker proved the configured origin binding with a fresh challenge and no-store owner response."
