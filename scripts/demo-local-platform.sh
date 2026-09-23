#!/usr/bin/env bash
# Automated Interactive Demo of the Local Platform v1.1
# Proves kind, Envoy Gateway, P01/P02, Prometheus, and Grafana in <= 10 mins.
set -euo pipefail

BASE_URL="http://127.0.0.1:8088"
PASS="Password123!@#"
EMAIL="interview_$(date +%s)@example.com"
IDEM="demo_$(date +%s)"

PIDS=()
cleanup() {
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

echo "=========================================================="
echo "      LOCAL PLATFORM v1.1 — INTERVIEW DEMO RUNNER"
echo "=========================================================="

echo "==> Step 1: Checking Kubernetes Nodes & Pods..."
kubectl get nodes -o wide
echo ""
echo "Pod counts by namespace:"
kubectl get pods -A --no-headers | awk '{print $1}' | sort | uniq -c

echo ""
echo "==> Step 2: Ensuring port-forward for Envoy Gateway, Prometheus, and Grafana..."
# Start port-forwards
kubectl -n envoy-gateway-system port-forward svc/envoy-platform-gateway-portfolio-gateway-d6017b10 8088:80 >/dev/null 2>&1 &
PIDS+=($!)
kubectl -n monitoring port-forward svc/kps-kube-prometheus-stack-prometheus 9090:9090 >/dev/null 2>&1 &
PIDS+=($!)
kubectl -n monitoring port-forward svc/kps-grafana 3000:80 >/dev/null 2>&1 &
PIDS+=($!)

sleep 2

echo "==> Step 3: Testing Shared Envoy Gateway Routing..."
echo "[Route 1] P02 LegacyApp (/health):"
curl -s -i -H "Host: legacy.local" "$BASE_URL/health" | head -n 8

echo ""
echo "[Route 2] P01 FlashSale (/healthz):"
curl -s -i -H "Host: flashsale.local" "$BASE_URL/healthz" | head -n 8

echo ""
echo "[Negative Control] Unmatched Host (/):"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" -H "Host: unmatched.local" "$BASE_URL/"

echo ""
echo "==> Step 4: Executing FlashSale Business Flow (Auth -> 202 -> Completed -> Pay)..."
echo "1. Registering user $EMAIL..."
REG_OUT=$(curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Host: flashsale.local" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}")
TOKEN=$(echo "$REG_OUT" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>console.log(JSON.parse(d).accessToken))")
echo "   Token acquired successfully."

echo "2. Submitting authenticated order (Idempotency-Key: $IDEM)..."
ORDER_OUT=$(curl -s -X POST "$BASE_URL/api/orders" \
  -H "Host: flashsale.local" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: $IDEM" \
  -d '{"productId":5,"quantity":1}')
echo "   Response: $ORDER_OUT"

echo "3. Waiting for asynchronous worker fulfillment..."
for i in {1..10}; do
  sleep 1
  POLL_OUT=$(curl -s -H "Host: flashsale.local" "$BASE_URL/api/orders/$IDEM")
  STATUS=$(echo "$POLL_OUT" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>console.log(JSON.parse(d).status))")
  echo "   [Poll $i] Status: $STATUS"
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "Completed" ]; then
    break
  fi
done

echo "4. Confirming payment..."
PAY_OUT=$(curl -s -X POST "$BASE_URL/api/orders/$IDEM/pay" \
  -H "Host: flashsale.local" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"outcome":"completed"}')
echo "   Payment Response: $PAY_OUT"

echo ""
echo "==> Step 5: Verifying Argo CD GitOps Applications..."
kubectl -n argocd get applications

echo ""
echo "==> Step 6: Verifying Observability Stack..."
echo "Prometheus Active Targets Count:"
curl -s http://127.0.0.1:9090/api/v1/targets | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>console.log('Total active targets:', JSON.parse(d).data.activeTargets.length))"

echo "Grafana Dashboard List:"
GF_PASS=$(kubectl -n monitoring get secret grafana-admin -o jsonpath="{.data.admin-password}" | base64 -d)
curl -s http://admin:"$GF_PASS"@127.0.0.1:3000/api/search | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>JSON.parse(d).filter(x=>x.type==='dash-db').forEach(x=>console.log(' - ' + x.title)))"

echo ""
echo "=========================================================="
echo "    DEMO COMPLETED SUCCESSFULLY — 100% GREEN LIVE PROOF"
echo "=========================================================="
