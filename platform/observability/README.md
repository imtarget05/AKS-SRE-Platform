# Local observability (L10)

Namespace `monitoring`, release `kps`, chart `prometheus-community/kube-prometheus-stack`
pinned at **91.5.0** (app v0.94.0).

## Install / upgrade

```bash
# once: namespace + admin secret (password lands in .local/, never in Git)
kubectl config use-context kind-local-platform
kubectl create namespace monitoring
PW="$(openssl rand -base64 18 | tr -d '/+=')"
kubectl -n monitoring create secret generic grafana-admin \
  --from-literal=admin-user=admin --from-literal=admin-password="$PW"

helm upgrade --install kps prometheus-community/kube-prometheus-stack \
  --version 91.5.0 -n monitoring \
  -f platform/observability/kube-prometheus-stack-values.yaml

kubectl apply -f platform/observability/argocd-servicemonitor.yaml \
  -f platform/observability/local-platform-prometheusrule.yaml \
  -f platform/observability/dashboards/
```

## Files

| File | Purpose |
|---|---|
| `kube-prometheus-stack-values.yaml` | pinned, laptop-sized chart values; Alertmanager off, control-plane scrapes off, selectors select-all |
| `argocd-servicemonitor.yaml` | scrapes every Argo CD component with a `metrics` port via the shared `part-of: argocd` label |
| `local-platform-prometheusrule.yaml` | the one proven alert, `LocalPlatformMetricSourceDown` |
| `dashboards/` | three ConfigMaps (`grafana_dashboard: "1"`): Local Platform · GitOps/Argo CD · FlashSale |

## Why these values (read before changing)

* **Alertmanager off** — the laptop has no receiver; the proof reads Prometheus rule state.
* **kubeControllerManager / kubeScheduler / etcd / kubeProxy scrapes + rules off** — kind binds those
  to 127.0.0.1, so `absent(up{job=…})` alerts would fire forever and bury the real signal.
* **`…SelectorNilUsesHelmValues: false`** — the Argo ServiceMonitor and our rule live outside the
  chart's release label; without this the operator would never select them.
* **`prometheusOperator.tls.enabled: false` + `admissionWebhooks.enabled: false`** — no webhook, no
  cert job, no pod stuck on a `tls-secret` that will never exist (observed `FailedMount ×10`).
* **kube-state-metrics `pullPolicy: IfNotPresent`** — `registry.k8s.io` dropped connections on this
  network twice, so the image is pulled once on the host and loaded into all nodes with
  `local/kind/load-image.sh`; nodes reuse the local copy.
* **Prometheus `emptyDir`** — history does not survive a pod restart. Documented; a local-path PVC is
  the next step if history matters.

Evidence: `docs/evidence/local-platform/l10-observability-PASS.md`.
