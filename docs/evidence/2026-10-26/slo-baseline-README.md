# 30-Day SLO Observation — Start + Measurement Baseline (2026-10-26)

## Observation window

- **Start (UTC): 2026-10-26T10:09:35Z** (first scrape in prometheus-mock TSDB, `alert-drill/prometheus-mock`, Prometheus 2.51.0)
- Baseline captured at: 2026-10-26T10:50:36Z
- **End target (UTC): 2026-11-25T10:09:35Z** (30 full days after start)
- Cluster: `aks-portfolio-dev` (live AKS)

## Services observed

| Service | Namespace | Probe endpoint | Data source |
|---|---|---|---|
| opsbridge-api | flashsale | `GET /healthz` | prometheus-mock server-side counters **+** in-cluster curl probe |
| bankops-api | quanlykho | `GET /api/v1/health/live`, `GET /api/v1/health/ready` | in-cluster curl probe (mock does not scrape quanlykho) |

`sre-demo-api` (the service `scripts/measure_sli_30day.py` is built for) is **not deployed** on this cluster, so the repo script cannot be used here; measurement uses the mock's real scraped metrics + direct probes.

## Baseline numbers (real, captured 2026-10-26T10:49:28–10:49:30Z + 40m mock window)

| SLI | opsbridge-api | bankops-api | PROPOSED threshold (docs/slo.md, deploy/sli/*.md) |
|---|---|---|---|
| Availability (2xx/3xx ÷ total) | **100.0%** (probe 30/30; mock: 14418×2xx, 6×4xx, 0×5xx over 40m) | **100.0%** (live 30/30, ready 30/30) | ≥ 99.9% / 30d |
| Error rate (5xx) | **0.0%** | **0.0%** | < 1% |
| Latency p95 | **54.55 ms** (probe) / ~0.95 ms (app histogram) | **13.65 ms** (live), **15.21 ms** (ready) | p95 < 500 ms |
| Latency p99 | 74.30 ms | 21.02 ms | p99 ≤ 500 ms |
| Throughput | 0.32 RPS (server-side, idle traffic) | n/a | ≥ 100 RPS sustained — **not measured yet**, needs load generator later in the window |

Full data: `slo-baseline-2026-10-26.json`, raw probe lines: `sli-probe-raw-output.txt`.

## How it was measured (reproducible)

**A. Prometheus-mock (server-side, opsbridge-api):**
```bash
kubectl -n alert-drill port-forward svc/prometheus-mock 9091:9090 &
# availability / codes
curl -s --data-urlencode 'query=sum by (code) (http_requests_received_total{job="opsbridge"})' \
  'http://localhost:9091/api/v1/query'
# latency percentiles (histogram_quantile over a window)
curl -s --data-urlencode 'query=histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="opsbridge"}[30m])))' \
  'http://localhost:9091/api/v1/query'
# fraction within 500ms (nearest bucket le=0.512)
curl -s --data-urlencode 'query=sum(increase(http_request_duration_seconds_bucket{job="opsbridge",le="0.512"}[1d])) / sum(increase(http_request_duration_seconds_count{job="opsbridge"}[1d]))' \
  'http://localhost:9091/api/v1/query'
```

**B. In-cluster probe (one-shot Job, 30 reqs/endpoint — did NOT touch any workload):**
```bash
kubectl -n default run sli-probe --restart=Never --rm -i \
  --image=curlimages/curl:8.11.1 --command -- sh -s <<'EOF'
probe() { name=$1; url=$2; i=0; while [ $i -lt 30 ]; do \
  curl -s -o /dev/null -w "${name}|%{http_code}|%{time_total}\n" "$url"; i=$((i+1)); done; }
probe opsbridge_healthz http://opsbridge-api.flashsale.svc.cluster.local/healthz
probe bankops_live http://<bankops-pod-IP>:8000/api/v1/health/live
probe bankops_ready http://<bankops-pod-IP>:8000/api/v1/health/ready
EOF
```
Note: use the **pod IP** for bankops-api (re-resolve each run with
`kubectl -n quanlykho get pod -l app.kubernetes.io/name=bankops-api -o jsonpath='{.items[0].status.podIP}'`).
Cross-namespace **ClusterIP** access to bankops-api currently times out from other namespaces even though pod-IP access works and no NetworkPolicy exists in quanlykho — see `known_findings` in the JSON; re-test before switching to ClusterIP.

## Daily runbook (no CronJob deployed)

`kube-prometheus-stack` is **not installed** on this cluster (only `prometheus-mock` in `alert-drill`), so no CronJob was created. Run manually daily (or schedule externally later):

```bash
cd /Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform
D=$(date -u +%F)
mkdir -p docs/evidence/2026-10-26/slo-daily/$D
# 1) server-side (opsbridge): run the 3 curl queries in section A, save JSON to slo-daily/$D/opsbridge-prom.json
# 2) probe: run section B with --max-time 5 per request, 30 reqs/endpoint, save to slo-daily/$D/probe-$D.txt
# 3) append a one-line summary (date, availability%, p95ms, 5xx) to docs/evidence/2026-10-26/slo-daily/summary.jsonl
```

Evidence location for the whole observation: `docs/evidence/2026-10-26/slo-daily/<YYYY-MM-DD>/`.

## 30-day plan

1. **Daily**: capture section A + B outputs into `slo-daily/<day>/` (10–30 requests per endpoint only; no stress).
2. **Weekly**: compute per-week availability/p95 and check drift; investigate any 5xx or p95 > 500 ms event with `kubectl logs` + mock alert logs (`http://alert-log-collector:8080/alerts`).
3. **Day 30 (~2026-11-25)**: aggregate the 30 daily files, compare against PROPOSED thresholds, write calibration report, update `docs/slo.md` with measured baselines, get stakeholder sign-off before thresholds become binding.
4. If a load generator is introduced for the 100 RPS throughput SLI, run it only in a dedicated low-concurrency window and record it as a separate evidence file (does not count as ambient traffic for availability SLI unless clearly labeled).

## Constraints honored

- No commits/pushes. No CronJob created. No existing workload modified — only one transient Job (`sli-probe-baseline`, ns `default`) which was deleted after capture.
- All numbers in the JSON come from actual `curl`/Prometheus query responses on 2026-10-26; nothing is fabricated.
