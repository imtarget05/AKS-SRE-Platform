# L10 — Prometheus, Grafana & Alert Proof — PASS

**Date:** 2026-09-23  
**Cluster:** `kind-local-platform` (Kubernetes v1.36.1)  
**Namespace:** `monitoring`  
**Azure mutated:** NO — local kind only.  

## L10.1 — Helm Stack & Running Components

Installed using pinned Helm chart `prometheus-community/kube-prometheus-stack` version **91.5.0**:

```text
monitoring   kps-grafana-78cdbfc6b6-77g2v                          3/3   Running   0   25m
monitoring   kps-kube-prometheus-stack-operator-7597778b67-zgz49   1/1   Running   0   14m
monitoring   kps-kube-state-metrics-67c8fc75bb-sw52g               1/1   Running   0   8m
monitoring   kps-prometheus-node-exporter-2sxgh                    1/1   Running   0   25m
monitoring   kps-prometheus-node-exporter-58qtl                    1/1   Running   0   25m
monitoring   kps-prometheus-node-exporter-cbj88                    1/1   Running   0   25m
monitoring   prometheus-kps-kube-prometheus-stack-prometheus-0     2/2   Running   0   13m
```

### Measured Active Scrape Targets (Prometheus API: 25 targets)
- **Kubernetes Core / Nodes**: Kubelet (cAdvisor, probes, node stats across 3 nodes) = `up`
- **Node Exporter**: DaemonSet on all 3 nodes (`control-plane`, `worker`, `worker2`) = `up`
- **Kube State Metrics**: Service & pod state metrics = `up`
- **CoreDNS**: 2 instances = `up`
- **API Server**: 1 instance = `up`
- **Argo CD Metrics**:
  - `argocd-metrics` (controller, 8082) = `up`
  - `argocd-server-metrics` (API server, 8083) = `up`
  - `argocd-repo-server` (repo server, 8084) = `up`
  - `argocd-applicationset-controller` (7000/8080) = `up`
- **Envoy Gateway**:
  - `envoy-gateway` control plane metrics (19001) = `up`

---

## L10.2 — Grafana Configuration & Dashboards

- Service: `kps-grafana` (`ClusterIP`, private access via `kubectl port-forward`).
- Version: **13.2.2-distroless**.
- Credentials: Read from secret `grafana-admin` (`admin-password`).

### Loaded Dashboards
Managed via sidecar ConfigMaps (`labels: grafana_dashboard: "1"`):
1. **Local Platform Overview** (`local-platform`): Node ready count, cluster CPU usage, memory consumption, node load.
2. **Argo CD GitOps Overview** (`argocd-gitops-overview`): Total applications, sync status (`Synced`/`OutOfSync`), health (`Healthy`/`Degraded`), and app table.
3. **Portfolio Workloads** (`portfolio-workloads-overview`): Pod CPU and memory tracking for `flashsale` and `legacyapp`, pod restart metrics.

---

## L10.3 — Live Alert Proof: LocalPlatformMetricSourceDown

- **PrometheusRule**: `local-platform-proof`
- **Alert**: `LocalPlatformMetricSourceDown`
- **Expression**: `absent(up{job=~".*kube-state-metrics.*"}) or up{job=~".*kube-state-metrics.*"} == 0` for `30s`
- **Proof Execution**:
  1. *Failure Injection*: `kube-state-metrics` pod temporarily removed/unscheduled during image rollout.
  2. *Alert Fired*: `activeAt: 2026-09-23T15:33:25.163677408Z`, state observed: **firing**.
  3. *Recovery*: Pod restarted with pre-loaded image, transitioned to `1/1 Running` at `15:34:25Z`.
  4. *Alert Resolved*: Prometheus re-evaluated the rule at `15:35:17Z` (~52s post-recovery). Observed state: **inactive**, `alerts: []`.
  5. *Zero Persistent Data Destroyed*: Tested safely against metric source without impacting databases.

## GATE

**L10: PASS** — Full Prometheus + Grafana stack operational, real multi-namespace scraping (K8s, Argo CD, Envoy Gateway), 3 custom dashboards loaded, alert fire-and-resolve cycle proven live with exact timestamps.
