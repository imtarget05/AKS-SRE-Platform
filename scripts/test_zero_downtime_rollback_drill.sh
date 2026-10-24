#!/usr/bin/env bash
# ==============================================================================
# test_zero_downtime_rollback_drill.sh:
# Empirical Rolling Update and Faulty Rollout Resilience Drill under Continuous Load.
# Proves:
#   1. Zero dropped requests during rolling update of order-api (2 replicas).
#   2. Fault isolation during broken deployment (ErrImagePull / bad probe).
#   3. Zero dropped requests while deployment is stalled and during rollout undo.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=8088
HOST_HEADER="flashsale.local"
URL="http://127.0.0.1:${PORT}/healthz"
TRAFFIC_LOG="/tmp/traffic_probe_$$.log"
CLEAN_DIGEST="flashsale/order-api@sha256:77a6e036df4f2cd2975b444989d0321a521feaaa1d9f6b2ac3e4cc97a325fb23"
BAD_IMAGE="flashsale/order-api:faulty-broken-$(date +%s)"

echo "=== [1/5] Setting up Envoy Gateway Port-Forward on :${PORT} ==="
kubectl -n envoy-gateway-system port-forward svc/envoy-platform-gateway-portfolio-gateway-d6017b10 ${PORT}:80 >/dev/null 2>&1 &
PF_PID=$!
sleep 2

cleanup() {
  echo "--- Drill Cleanup ---"
  kill $PROBER_PID 2>/dev/null || true
  kill $PF_PID 2>/dev/null || true
  # Ensure clean deployment state
  kubectl set image deployment/order-api order-api=flashsale/order-api:local -n flashsale >/dev/null 2>&1 || true
  rm -f "$TRAFFIC_LOG"
}
trap cleanup EXIT

echo "Verifying baseline connectivity..."
curl -s -f -H "Host: ${HOST_HEADER}" "${URL}" >/dev/null || {
  echo "ERROR: Could not reach ${URL}"
  exit 1
}
echo "Baseline healthy."

echo ""
echo "=== [2/5] Starting High-Frequency Background Traffic Probe (20 req/s) ==="
rm -f "$TRAFFIC_LOG"
python3 -c "
import urllib.request, time, sys

url = '${URL}'
headers = {'Host': '${HOST_HEADER}'}
log_file = '${TRAFFIC_LOG}'

with open(log_file, 'w') as f:
    while True:
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                code = resp.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            code = 0
        lat_ms = (time.time() - t0) * 1000.0
        f.write(f'{time.time():.4f},{code},{lat_ms:.2f}\n')
        f.flush()
        time.sleep(0.05)
" &
PROBER_PID=$!
sleep 1

echo "Prober running with PID ${PROBER_PID}."

echo ""
echo "=== [3/5] Executing Normal Rolling Update with Immutable Digest ==="
echo "Target Image: ${CLEAN_DIGEST}"
kubectl set image deployment/order-api order-api="${CLEAN_DIGEST}" -n flashsale
kubectl rollout status deployment/order-api -n flashsale --timeout=60s
echo "Rolling update completed successfully."

echo ""
echo "=== [4/5] Injecting Broken Deployment (Fault Simulation: Nonexistent Image) ==="
echo "Target Image: ${BAD_IMAGE}"
kubectl set image deployment/order-api order-api="${BAD_IMAGE}" -n flashsale

echo "Waiting 8 seconds while deployment attempts rollout and stalls..."
sleep 8

echo "Inspecting pod statuses during broken rollout:"
kubectl get pods -n flashsale -l app=order-api -o wide

echo "Initiating automated rollback (rollout undo)..."
UNDO_START=$(date +%s%N)
kubectl rollout undo deployment/order-api -n flashsale
kubectl rollout status deployment/order-api -n flashsale --timeout=60s
UNDO_END=$(date +%s%N)
UNDO_DURATION_MS=$(awk -v s="$UNDO_START" -v e="$UNDO_END" 'BEGIN { printf "%.2f", (e - s)/1000000 }')
echo "Rollback completed in ${UNDO_DURATION_MS} ms."

echo ""
echo "=== [5/5] Analyzing Telemetry Collected During the Drill ==="
kill $PROBER_PID 2>/dev/null || true

python3 -c "
lines = open('${TRAFFIC_LOG}').readlines()
total = len(lines)
codes = {}
latencies = []
for line in lines:
    parts = line.strip().split(',')
    if len(parts) == 3:
        code = int(parts[1])
        lat = float(parts[2])
        codes[code] = codes.get(code, 0) + 1
        latencies.append(lat)

latencies.sort()
p50 = latencies[int(len(latencies)*0.50)] if latencies else 0
p95 = latencies[int(len(latencies)*0.95)] if latencies else 0
p99 = latencies[int(len(latencies)*0.99)] if latencies else 0
max_lat = max(latencies) if latencies else 0
avg_lat = sum(latencies)/len(latencies) if latencies else 0

success = codes.get(200, 0)
failed = total - success
availability = (success / total * 100.0) if total > 0 else 0.0

print(f'Total requests probed : {total}')
print(f'HTTP 200 Successes    : {success}')
print(f'Dropped / 5xx / Errors: {failed}')
print(f'Status Breakdown      : {codes}')
print(f'Empirical Availability: {availability:.2f}%')
print(f'Latency p50           : {p50:.2f} ms')
print(f'Latency p95           : {p95:.2f} ms')
print(f'Latency p99           : {p99:.2f} ms')
print(f'Latency avg           : {avg_lat:.2f} ms')
print(f'Latency max           : {max_lat:.2f} ms')

assert failed == 0, f'Expected 0 failed requests, got {failed}'
assert availability == 100.0, f'Expected 100% availability, got {availability}%'
print('VERIFICATION PASSED: Zero dropped requests during rolling update and fault injection/rollback!')
"

echo "=== DRILL COMPLETE ==="
