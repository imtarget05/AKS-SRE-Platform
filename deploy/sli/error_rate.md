# Service Level Indicators (SLIs) for AKS SRE Platform

## error_rate
- **Definition**: Fraction of requests that result in a 5xx status code.
- **Formula**: `5xx_count / total_request_count`
- **Target**: < 1% (over rolling time window)
- **Measurement**: Prometheus metric `http_requests_total` with `code=~"5.."`
- **Prometheus Query**: `(sum(rate(http_requests_total{code=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))`

## latency_p95
- **Definition**: 95th percentile of request latency.
- **Formula**: percentile95(latency_ms)
- **Target**: < 500ms
- **Measurement**: Prometheus histogram of request latency in ms
- **Prometheus Query**: `histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[5m])) by (le)`

## availability
- **Definition**: Fraction of time the service is available (not degraded).
- **Formula**: `available_requests / total_requests`
- **Target**: > 99.9% (over 30 days)
- **Measurement**: Uptime monitoring via synthetic health checks
- **Prometheus Query**: `(1 - sum(rate(http_requests_total{code=~"5..|4.."}[1d])) / sum(rate(http_requests_total[1d]))`

## hpa_reaction_time
- **Definition**: Time between HPA scale-up trigger and actual pod scheduling.
- **Formula**: `last_scale_up_timestamp - first_pod_ready_timestamp`
- **Target**: < 30s
- **Measurement**: Custom metric from Kubernetes HPA events
- **Prometheus Query**: `min by (namespace, deployment) (kube_hpa_status_last_scale_time_seconds{action="scale-up"})`