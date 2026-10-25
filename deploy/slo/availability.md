# Service Level Objectives (SLOs) for AKS SRE Platform

## availability SLO
- **Target**: 99.9% over 30 days
- **Error Budget**: 0.1% of total request time may be spent in degraded state or outages
- **Calculation**: `(1 - (5xx_count_30d / total_request_count_30d)) >= 0.999`
- **Rolling Window**: 30-day moving availability percentage
- **Alerting**: 
  - Warning when error budget remaining < 20% (i.e., availability < 99.97%)
  - Critical when error budget remaining < 10% (i.e., availability < 99.99%)
- **Runbook**: docs/runbooks/availability-slo.md

**SLO Definition in Prometheus:**
```
slo_availability = (1 - sum(rate(http_requests_total{code=~"5.."}[1d])) / sum(rate(http_requests_total[1d]))) * 100
alert: AvailabilitySLOWarning
  expr: slo_availability < 99.97
  for: 2h
  labels:
    severity: warning
    slo: availability
  annotations:
    summary: "Availability SLO warning (99.97% remaining budget)"
    description: "Availability has dropped below 99.97%. Current availability: {{ slo_availability }}%. Error budget remaining: {{ 100 - slo_availability }}%"
    runbook: docs/runbooks/availability-slo.md

alert: AvailabilitySLOCritical
  expr: slo_availability < 99.99
  for: 1h
  labels:
    severity: critical
    slo: availability
  annotations:
    summary: "Availability SLO critical (99.99% remaining budget)"
    description: "Availability has dropped below 99.99%. Current availability: {{ slo_availability }}%. Error budget remaining: {{ 100 - slo_availability }}%"
    runbook: docs/runbooks/availability-slo.md
```

**SLO Status Dashboard:**
- ✅ SLO on track: availability >= 99.97% (error budget > 97% remaining)
- ⚠️ SLO at risk: 99.9% <= availability < 99.97% (error budget 97-99% remaining)
- ❌ SLO breached: availability < 99.9% (error budget < 97% consumed)