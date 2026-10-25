# Service Level Indicators (SLIs) for AKS SRE Platform

## latency_p95
- **Definition**: 95th percentile of request latency across all endpoints.
- **Formula**: `histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[5m])) by (le))`
- **Target**: p95 < 500ms over 1m rolling window
- **Measurement**: Application-level request latency histogram
- **Prometheus Query**: `histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[5m])) by (le))`

## error_rate
- **Definition**: Fraction of requests that result in a 5xx or 4xx status code (client + server errors).
- **Formula**: `(5xx + 4xx_count) / total_request_count`
- **Target**: < 5% (over rolling time window, but SLO target is 1% for 5xx only)
- **Measurement**: Prometheus metric `http_requests_total` with error codes
- **Prometheus Query**: `(sum(rate(http_requests_total{code=~"4..|5.."}[1m])) / sum(rate(http_requests_total[1m]))`

## availability
- **Definition**: Percentage of time the service is fully available (no errors, no outages).
- **Formula**: `1 - (error_budget_consumed / total_error_budget)`
- **Target**: > 99.9% over 30 days
- **Measurement**: Uptime synthetic health checks + error rate integration
- **Prometheus Query**: `(1 - sum(rate(http_requests_total{code=~"5.."}[1d])) / sum(rate(http_requests_total[1d]))`

## hpa_reaction_time
- **Definition**: Time between HPA scale-up decision and pod readiness.
- **Formula**: `kube_hpa_status_last_scale_time_seconds - pod_ready_timestamp`
- **Target**: < 30s
- **Measurement**: HPA event timestamps + pod startup metrics
- **Prometheus Query**: `min by (deployment) (kube_hpa_status_last_scale_time_seconds{action="scale-up"})`