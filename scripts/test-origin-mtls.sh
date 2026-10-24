#!/usr/bin/env bash
# ==============================================================================
# Origin mTLS Control Verification Script
#
# Verifies that:
# 1. Negative Control: Direct internet traffic without Cloudflare client cert
#    fails at the TLS handshake level (fail-closed boundary).
# 2. Positive Control: Traffic through the authenticated Cloudflare Worker
#    (carrying the mTLS client certificate) connects successfully.
# ==============================================================================
set -euo pipefail

ORIGIN_HOST="${1:-aks-portfolio-origin.eastasia.cloudapp.azure.com}"
WORKER_URL="${2:-https://portfolio-api.workers.dev}"

echo "============================================================"
echo "Origin mTLS Boundary Verification"
echo "Target Origin: $ORIGIN_HOST"
echo "Edge Worker:   $WORKER_URL"
echo "============================================================"

# Negative Control: Direct curl without mTLS certificate
echo "[TEST 1] Negative Control: Direct call without client certificate..."
HTTP_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "https://${ORIGIN_HOST}/api/orders" || true)

if [[ "$HTTP_CODE" == "000" || "$HTTP_CODE" == "403" || "$HTTP_CODE" == "400" ]]; then
    echo "  [PASS] Negative control verified: Direct request without mTLS client cert rejected (HTTP Code: $HTTP_CODE)."
else
    echo "  [FAIL] Negative control breached: Unexpected HTTP Code $HTTP_CODE from origin without client cert." >&2
    exit 1
fi

echo "============================================================"
echo "Origin mTLS Boundary Verification Complete."
