# AKS 30-day SLI evidence procedure

Status: **proposed, not accepted**. This procedure records 30 complete UTC days of the `sre-demo-api`'s own HTTP telemetry. It cannot by itself establish availability through Cloudflare, Envoy Gateway, or AKS. An external synthetic probe and independent sign-off are required for a production SLO claim.

## Contract and targets

The application emits `sre_api_requests_total{service,route,method,status}` and `sre_api_request_duration_seconds_bucket{service,route,method,le}` in [`app/sre-demo-api/src/observability.js`](../../app/sre-demo-api/src/observability.js). The collector in [`scripts/measure_sli_30day.py`](../../scripts/measure_sli_30day.py) counts only `/api/work` and `/api/dependency`; health, `/metrics`, internal probes and the test-only `/api/fail` route are excluded. HTTP 5xx is an error; 2xx, 3xx and expected 4xx count as served requests. The histogram contains all included requests, including 5xx.

| Proposed objective | Exact 30-day calculation | Decision |
| --- | --- | --- |
| Availability ≥ 99.9% | `1 - sum(5xx request increases) / sum(all request increases)` | Primary request-based error budget is 0.1%. |
| Server error rate < 1% | `sum(5xx) / sum(all requests)` | Secondary guard; weaker than the 99.9% objective. |
| p95 latency ≤ 500 ms | `sum(le="0.5" histogram bucket increases) / sum(histogram count increases) ≥ 0.95` | Bucket-based equivalent for the included request population. |

Each daily value uses Prometheus `increase(...[1d])` evaluated at the next UTC midnight. The collector stores the exact queries, window, collection time and immutable application image digest with the response values. Summing daily counter increases over 30 contiguous days produces the 30-day request and histogram ratios. `increase` extrapolates across scrape samples, so these ratios are estimates and the raw query responses must be retained for audit if a disputed boundary matters. Never average daily percentages or daily p95 values.

The current [`docs/slo.md`](../slo.md) and draft `slo-burn-rate-rules.yaml` refer to generic `http_requests_total` names; those are **not** the metric names emitted by this application. Reconcile those drafts with the real metrics before installing their alerts. The AKS Helm values currently retain only **15 days** of Prometheus data, so daily evidence files or a reviewed long-term metrics store are necessary for a 30-day window. This runbook does not change retention or install a store.

## Prerequisites before day 1

1. Deploy and verify a `ServiceMonitor` that scrapes `sre-demo-api` `/metrics` in AKS. The current observability overlay lists monitors for Argo CD and Envoy, but no demo API monitor. Check Prometheus Targets and run the four collector queries manually; an absent series is a gap, not zero errors.
2. Confirm the public synthetic probe covers Cloudflare → Gateway → workload at a fixed interval and archives every result, including transport failures and 5xx. Record probe location, URL, interval, maintenance policy and missing-sample policy. The in-process counters cannot see rejected edge requests, DNS/TLS failures or periods when all pods are down.
3. Record the exact app image digest and current Git/Argo revision. Set a UTC start date after scrape and probe coverage are verified. Alertmanager notification and 30-day Prometheus retention are separate gates.
4. Define on-call owner and reviewer. Proposed targets become binding only after 30 observed days and stakeholder sign-off.

## Collect and archive once per UTC day

Use a local port-forward or a protected read-only Prometheus endpoint; never put credentials in a URL. The command is read-only. Run it at least five minutes after the previous UTC day ends, and schedule it daily. Replace the example digest with the digest actually deployed during that day.

```bash
kubectl --context aks-portfolio-dev -n monitoring port-forward svc/kps-kube-prometheus-stack-prometheus 9090:9090

python3 scripts/measure_sli_30day.py collect \
  --day 2026-10-26 \
  --prometheus-url http://127.0.0.1:9090 \
  --app-image-digest sha256:<actual-64-hex-digest> \
  --out-dir docs/evidence/aks-sli-daily
```

The collector refuses missing aggregate series, inconsistent request/histogram counts, future windows and overwrite of a daily file. Archive the JSON, Prometheus target status, public probe samples, Argo revision and image digest outside the working tree as immutable evidence. If a day is missed, recover it within the 15-day retention window from the exact UTC query time; otherwise restart the 30-day acceptance window. Any scrape gap, no-traffic day, missing probe sample or release mismatch needs investigation and cannot be silently counted as healthy time.

After 30 consecutive daily files:

```bash
python3 scripts/measure_sli_30day.py report \
  --end-day 2026-11-24 \
  --in-dir docs/evidence/aks-sli-daily
```

The report refuses a missing day or changed metric contract and always prints `INTERNAL_API_ONLY_EXTERNAL_PROBE_AND_REVIEW_REQUIRED`. To accept the platform SLO, attach the external probe's 30-day numerator/denominator, scrape coverage, deployment digests, incident exclusions approved in advance, and an independent reviewer signature. Do not turn the report's proposed-target booleans into a “production 100%” claim by themselves.
