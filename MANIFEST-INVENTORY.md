# Manifest Inventory

Every Kubernetes YAML owned by this repository must appear in this file with an
explicit classification. The gate is enforced by
[`gitops/validate-gitops.py`](gitops/validate-gitops.py) (`manifest-inventory`
check): **adding a YAML file under `kubernetes/` without classifying it here
fails CI.** There are no silent orphans.

## Classification vocabulary

| Status | Meaning |
|---|---|
| `RENDERED` | Included in a `kustomization.yaml` and validated by kubeconform in CI. Deployed. |
| `LEGACY_NOT_DEPLOYED` | Retained as history or design record. Not in any kustomization. Never deployed from this repo. |
| `EXTERNAL_WORKLOAD_REFERENCE` | Describes a workload owned by another repository. This repo holds a reference/contract, not the workload. |
| `SUPERSEDED` | Contradicted or replaced. Kept for the record until the replacement lands, then removed. |
| `FUTURE_PHASE` | Planned and owned by this repo, not yet written. Must name the phase. |

## `kubernetes/` — legacy tree

| File | Status | Reason |
|---|---|---|
| `kubernetes/kustomization.yaml` | `RENDERED` | The only active kustomization here. Renders `namespace` + `keda-autoscaler` + `keda-trigger-auth`. |
| `kubernetes/namespace.yaml` | `RENDERED` | `flashsale` namespace. Belongs to P01; harmless and required by the two manifests below. |
| `kubernetes/keda-autoscaler.yaml` | `LEGACY_NOT_DEPLOYED` | RabbitMQ `QueueLength` ScaledObject targeting `order-worker`. Contradicted by `order-worker.yaml`, which injects a **Service Bus** connection string. The two halves disagree on the broker; this file is not evidence of working event-driven autoscaling. Replaced by the KEDA decision in the Phase D/F workload. |
| `kubernetes/keda-trigger-auth.yaml` | `LEGACY_NOT_DEPLOYED` | `TriggerAuthentication` for a `rabbitmq-secret` that **nothing in this repository creates**. It was created out-of-band in a later phase. Undeployable as written. |
| `kubernetes/order-worker.yaml` | `EXTERNAL_WORKLOAD_REFERENCE` | A reference copy of P01's worker, kept so the GitOps/PDB story has something concrete. Not a workload this repo owns, has no probes, no securityContext, and pins `:latest` against a placeholder registry. Replaced by `app/sre-demo-api`. |
| `kubernetes/pod-disruption-budget.yaml` | `SUPERSEDED` | `PodDisruptionBudget` selecting `app: order-api`, a workload that **does not exist in this repository**. Unmatched selector, so it can never bind. Replaced by the PDB in `deploy/base`. |

## `platform/` — cluster platform

| File | Status | Reason |
|---|---|---|
| `platform/envoy-gateway/gateway/*.yaml` | `RENDERED` | GatewayClass / Gateway / EnvoyProxy. Validated by kubeconform via `kustomize`. |
| `platform/envoy-gateway/proof-backend/*.yaml` | `RENDERED` | Backend used by the north-south proof. |
| `platform/argocd/appproject.yaml` | `RENDERED` | The AppProject both Applications live in. Validated by `gitops/validate-gitops.py`. |
| `platform/argocd/applications/*.yaml` | `SUPERSEDED` | Duplicates of `gitops/applications/*.yaml` for the local platform. The `gitops/` tree is canonical; these drift. |

## `platform/observability/` — monitoring

| File | Status | Reason |
|---|---|---|
| `platform/observability/dashboards/*.yaml` | `RENDERED` | Grafana dashboards provisioned from Git. |
| `platform/observability/*servicemonitor*.yaml` | `RENDERED` | ServiceMonitors for Argo CD and Envoy Gateway. |
| `platform/observability/local-platform-prometheusrule.yaml` | `RENDERED` | The one alert rule with real firing/resolving evidence (`docs/evidence/local-platform/l10-observability-PASS.md`). |
| `platform/observability/kube-prometheus-stack-values.yaml` | `LEGACY_NOT_DEPLOYED` | Helm values retained for the local stack; not applied by any CI path. |

## `app/` and `deploy/`

| Path | Status | Reason |
|---|---|---|
| `app/sre-demo-api` | `FUTURE_PHASE` (F) | The repo-owned workload: OTel SDK, RED metrics, structured logs with `trace_id`, non-root, graceful shutdown. |
| `deploy/base` | `FUTURE_PHASE` (F) | Deployment / Service / HTTPRoute / ConfigMap / ServiceAccount / HPA / PDB / NetworkPolicy, with all three probes, resources, `securityContext` and `topologySpreadConstraints`. |
| `deploy/overlays/validation` | `FUTURE_PHASE` (F) | The only overlay created in the first pass. No `prod` overlay is created until one is genuinely maintained. |

## Why this file exists

Two of the six manifests in `kubernetes/` are undeployable as written
(unmatched PDB selector, absent Secret) and two more contradict each other on
the broker. `kubectl kustomize kubernetes/` is green regardless, because
kustomize does not know what a selector matches or whether a Secret exists.
Rendering green therefore proves nothing here — this inventory is what makes the
tree honest.

## Rules

1. Every `*.yaml` / `*.yml` under `kubernetes/` must be classified above. The
   path string `kubernetes/<name>` must appear verbatim.
2. A `RENDERED` file must be reachable from a `kustomization.yaml` and must
   pass kubeconform. Verified by the PR gate, not by this file.
3. `SUPERSEDED` entries must name their replacement or the phase that removes
   them.
4. `FUTURE_PHASE` entries must name a phase, so an unbuilt directory cannot
   masquerade as planned-and-forgotten.
