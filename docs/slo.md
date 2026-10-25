# SLI/SLO Definitions for AKS-SRE-Platform Core Services
#
# This document defines Service Level Indicators (SLIs) and Service Level Objectives (SLOs)
# for the core services in the AKS-SRE-Platform. These are PROPOSED thresholds pending
# a 30-day observation period on Azure (Phase K). After observation, thresholds will be
# calibrated based on actual baseline measurements.
#
# Observation period: 30 days (required before thresholds become binding)
# Review cadence: Monthly during observation, quarterly after

---

## Service: sre-demo-api (Demo API Workload)

### SLI: Availability
**Definition**: Ratio of successful HTTP requests (2xx, 3xx) to total requests
**Measurement**: `sum(rate(http_requests_total{job="sre-demo-api",code=~"2..|3.."}[5m])) / sum(rate(http_requests_total{job="sre-demo-api"}[5m]))`
**Target (Proposed)**: ≥ 99.9% over 30-day rolling window
**Error Budget**: 0.1% = ~43 minutes downtime/month

### SLI: Latency (p99)
**Definition**: 99th percentile of HTTP request duration
**Measurement**: `histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="sre-demo-api"}[5m])) by (le))`
**Target (Proposed)**: ≤ 500ms for p99 over 5-minute window
**Error Budget**: Requests exceeding 500ms should be < 1% of total

### SLI: Throughput
**Definition**: Requests per second sustained without degradation
**Measurement**: `sum(rate(http_requests_total{job="sre-demo-api"}[1m]))`
**Target (Proposed)**: ≥ 100 RPS sustained with p99 latency ≤ 500ms

### SLI: Saturation (CPU)
**Definition**: CPU utilization relative to request limit
**Measurement**: `sum(rate(container_cpu_usage_seconds_total{namespace="default",pod=~"sre-demo-api-*"}[5m])) / sum(kube_pod_container_resource_limits{namespace="default",pod=~"sre-demo-api-*",resource="cpu"})`
**Target (Proposed)**: ≤ 70% average utilization (matches HPA target)

---

## Service: argocd (GitOps Controller)

### SLI: Availability
**Definition**: Argo CD API server responsiveness
**Measurement**: `up{job="argocd-server-metrics"} == 1`
**Target (Proposed)**: ≥ 99.95% over 30-day rolling window
**Error Budget**: 0.05% = ~21 minutes downtime/month

### SLI: Sync Latency
**Definition**: Time from Git commit to cluster reconciliation
**Measurement**: `time() - argocd_app_last_succeeded_sync_timestamp` (when app is OutOfSync)
**Target (Proposed)**: ≤ 5 minutes for automated sync apps

### SLI: Application Health
**Definition**: Ratio of healthy applications to total managed applications
**Measurement`: `sum(argocd_app_info{health_status="Healthy"}) / sum(argocd_app_info)`
**Target (Proposed)**: 100% (all apps healthy at all times)

---

## Service: prometheus (Monitoring Stack)

### SLI: Availability
**Definition**: Prometheus query API responsiveness
**Measurement**: `up{job="prometheus"} == 1`
**Target (Proposed)**: ≥ 99.9% over 30-day rolling window

### SLI: Scrape Success Rate
**Definition**: Ratio of successful target scrapes to total targets
**Measurement**: `sum(up) / count(up)`
**Target (Proposed)**: ≥ 99% (allowing for transient target churn)

### SLI: Rule Evaluation Latency
**Definition**: Time to evaluate all recording/alerting rules
**Measurement**: `prometheus_rule_evaluation_duration_seconds_sum / prometheus_rule_evaluation_duration_seconds_count`
**Target (Proposed)**: p99 ≤ 10 seconds

---

## Service: cluster-autoscaler

### SLI: Scale Decision Latency
**Definition**: Time from pod pending to node provisioned
**Measurement**: Custom metric from scale-event logger (node_event timestamp - pod pending timestamp)
**Target (Proposed)**: p99 ≤ 5 minutes for standard node pools

### SLI: Node Provision Success Rate
**Definition**: Ratio of successful node provisions to attempted
**Measurement**: `increase(cluster_autoscaler_nodes_added_total[1h]) / increase(cluster_autoscaler_scale_total{action="scale_up"}[1h])`
**Target (Proposed)**: 100% (failed provisions alert immediately)

---

## Error Budget Policy

| SLO Tier | Error Budget | Action When Exhausted |
|----------|-------------|----------------------|
| Critical (Availability) | 0.1% / month | Freeze non-critical deployments, incident review required |
| High (Latency) | 1% requests > threshold | Performance investigation, capacity planning |
| Medium (Throughput) | 10% below target | Scale review, architecture assessment |

---

## Alerting Rules Derived from SLOs

### Burn Rate Alerts (Multi-Window, Multi-Burn-Rate)
For each availability SLO, alert on:
- **Fast burn**: 2% error budget consumed in 1 hour (pages on-call)
- **Slow burn**: 5% error budget consumed in 6 hours (pages on-call)
- **Very slow burn**: 10% error budget consumed in 3 days (ticket)

### Example: sre-demo-api Availability Burn Rate
```yaml
- alert: SreDemoApiAvailabilityFastBurn
  expr: |
    (1 - sum(rate(http_requests_total{job="sre-demo-api",code=~"2..|3.."}[1h]))
       / sum(rate(http_requests_total{job="sre-demo-api"}[1h])))
    > 0.002  # 2% error budget in 1h = 14.4x burn rate for 99.9% SLO
  for: 2m
  labels:
    severity: critical
    slo: sre-demo-api-availability
  annotations:
    summary: "sre-demo-api availability fast burn (2% budget in 1h)"
```

---

## 30-Day Observation Requirement

**ALL thresholds marked "Proposed" require a 30-day observation period on Azure before becoming binding.**

During observation:
1. Collect actual baseline measurements for each SLI
2. Document observed percentiles (p50, p90, p99, p99.9)
3. Calibrate thresholds to be achievable but meaningful
4. Update this document with measured baselines
5. Get stakeholder sign-off on final thresholds

**Do not treat proposed thresholds as operational contracts until observation is complete.**

---

## Reference Implementation

The following PrometheusRule manifests implement the SLO-derived alerts:
- `deploy/base/observability/slo-alerts.yaml` (to be created)
- `deploy/base/observability/slo-burn-rate-rules.yaml` (to be created)

The scale-event logger (`scripts/log_scale_events.py`) provides the data for cluster-autoscaler SLIs.