# Service Level Objectives (SLOs) for AKS SRE Platform

## latency_p95 SLO
- **Target**: p95 < 500ms over 30 days
- **Error Budget**: Exceeding 500ms p95 consumes error budget
- **Calculation**: `histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1d])) by (le)) < 0.5s` over 30-day average
- **Rolling Window**: 30-day moving average of p95 values
- **Alerting**: Notify when p95 exceeds 500ms for 3 consecutive days
- **Runbook**: docs/runbooks/latency-p95-slo.md

**SLO Definition in Prometheus:**
```
slo_latency_p95 = histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1d])) by (le))
alert: LatencyP95SLOBreached
  expr: slo_latency_p95 > 0.5
  for: 3d
  labels:
    severity: warning
    slo: latency_p95
  annotations:
    summary: "Latency p95 SLO breached (500ms over 30 days)"
    description: "p95 latency has exceeded 500ms over the last 30 days. Current p95: {{ slo_latency_p95 | humanize_ms }}s"
    runbook: docs/runbooks/latency-p95-slo.md
```

**SLO Status Dashboard:**
- ✅ SLO on track: p95 <= 500ms (current p95 within target)
- ⚠️ SLO at risk: p95 > 500ms but <= 600ms (degraded performance)
- ❌ SLO breached: p95 > 600ms (significantly above target)