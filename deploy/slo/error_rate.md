# Service Level Objectives (SLOs) for AKS SRE Platform

## error_rate SLO
- **Target**: 99% over 30 days
- **Error Budget**: 1% of total requests may result in 5xx errors
- **Calculation**: `(5xx_count_30d / total_request_count_30d) <= 0.01`
- **Rolling Window**: 30-day moving average
- **Alerting**: Notify when error budget remaining < 10% (i.e., SLO slipping below 99.9%)
- **Runbook**: docs/runbooks/error-rate-slo.md

**SLO Definition in Prometheus:**
```
slo_error_rate = (sum(rate(http_requests_total{code=~"5.."}[1d])) / sum(rate(http_requests_total[1d]))) * 100
alert: ErrorRateSLOBreached
  expr: slo_error_rate > 1
  for: 1h
  labels:
    severity: warning
    slo: error_rate
  annotations:
    summary: "Error rate SLO breached (99% over 30 days)"
    description: "Error rate has exceeded 1% over the last 30 days. Current rate: {{ slo_error_rate }}%"
    runbook: docs/runbooks/error-rate-slo.md
```

**SLO Status Dashboard:**
- ✅ SLO on track: error_rate <= 99% of budget consumed
- ⚠️ SLO at risk: error_rate > 99% but <= 99.5% of budget consumed
- ❌ SLO breached: error_rate > 99.5% of budget consumed