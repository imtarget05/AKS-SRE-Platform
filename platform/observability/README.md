# Observability profiles: local kind and AKS

The two profiles use the same pinned `prometheus-community/kube-prometheus-stack`
chart version **91.5.0**. The local values file disables Alertmanager and is
only for kind. The AKS values file enables Alertmanager with an externally
provisioned receiver configuration; never install the local values on AKS.

## Local kind (L10)

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

kubectl apply -k deploy/base/observability/
```

## Files

| File | Purpose |
|---|---|
| `kube-prometheus-stack-values.yaml` | pinned, laptop-sized chart values; Alertmanager off, control-plane scrapes off, selectors select-all |
| `deploy/base/observability/argocd-servicemonitor.yaml` | scrapes every Argo CD component with a `metrics` port via the shared `part-of: argocd` label |
| `deploy/base/observability/dashboards.yaml` + `local-platform-dashboard.yaml` | Grafana dashboard ConfigMaps, rendered by `deploy/base/observability/kustomization.yaml` |
| `deploy/base/observability/local-platform-prometheusrule.yaml` | the one proven local alert, `LocalPlatformMetricSourceDown` |
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

## AKS installation and alert proof

The [AKS acceptance baseline](../../docs/acceptance/2026-10-26-platform-baseline.md)
records that the operator CRDs and an AKS fire/resolve cycle were not proven at
the previous release. A local manifest render is not an AKS result.
The AKS values disable etcd, controller-manager, scheduler and kube-proxy
scrapes/default rules because these managed control-plane endpoints are not
exposed to this cluster. Kubelet, API server, node exporter, kube-state-metrics
and workload rules remain enabled; confirm their targets after installation.

1. Review `helm template kps prometheus-community/kube-prometheus-stack
   --version 91.5.0 --namespace monitoring -f
   platform/observability/kube-prometheus-stack-aks-values.yaml` and
   `kubectl kustomize deploy/overlays/aks-observability`. Check the chart and
   image digests, resource requests, storage/retention, rollback and the current
   cluster context before installing.
2. Provision `monitoring/grafana-admin` with keys `admin-user` and
   `admin-password`, and `monitoring/alertmanager-portfolio` with key
   `alertmanager.yaml` through the approved secret system. The Alertmanager
   config must route `team=platform-sre` to a real operator receiver. Keep the
   config and credential values out of Git. Confirm both Secrets exist without
   printing their contents.
3. After review, install the pinned operator chart and CRDs, then apply only
   the observability overlay. The overlay excludes demo workloads and the
   local kind proof rule:

   ```bash
   kubectl --context aks-portfolio-dev get secret -n monitoring grafana-admin alertmanager-portfolio -o name
   helm upgrade --install kps prometheus-community/kube-prometheus-stack \
     --version 91.5.0 --namespace monitoring --kube-context aks-portfolio-dev \
     -f platform/observability/kube-prometheus-stack-aks-values.yaml --wait --atomic
   kubectl --context aks-portfolio-dev get crd servicemonitors.monitoring.coreos.com prometheusrules.monitoring.coreos.com
   kubectl --context aks-portfolio-dev apply -k deploy/overlays/aks-observability
   ```

4. Verify Prometheus discovers `argocd`, `envoy-gateway` and
   `kube-state-metrics` targets before a fault drill. Confirm the
   `AKSMonitoringTargetDown` rule is loaded and initially inactive. If the
   kube-state-metrics job label does not match the rule's regex, correct and
   review the selector before injection. Confirm Alertmanager has a non-null
   receiver and the intended operator can receive it.
5. In an approved maintenance window, run the **read-only** capture script
   below. Once it reports a healthy baseline, temporarily scale the
   `kps-kube-state-metrics` Deployment to zero, record its original replica
   count, and restore that count as soon as the alert reaches Alertmanager.
   This briefly removes state metrics; do not run it during a separate incident.

   ```bash
   python3 scripts/capture_aks_alert_cycle.py \
     --context aks-portfolio-dev \
     --output /private/tmp/aks-alert-cycle-2026-10-26.json
   # In another terminal after baseline is healthy:
   kubectl --context aks-portfolio-dev -n monitoring get deployment kps-kube-state-metrics -o jsonpath='{.spec.replicas}'
   kubectl --context aks-portfolio-dev -n monitoring scale deployment kps-kube-state-metrics --replicas=0
   # Restore the saved original replica count immediately after fire is observed.
   kubectl --context aks-portfolio-dev -n monitoring scale deployment kps-kube-state-metrics --replicas=1
   ```

   The `--replicas=1` example is valid only if the saved original count was 1.
   Verify target recovery and the script's `result: complete`; attach separate
   redacted receiver-delivery proof, cluster revision, image digest, UTC times,
   and independent reviewer sign-off. The script records Alertmanager receipt,
   **not** delivery to a person, and deliberately sets
   `notification_delivery_verified: false`.
