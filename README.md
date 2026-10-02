# AKS / SRE Platform Blueprint

> **Runtime decision (2026-10-02):** verification runs on a **real AKS
> cluster**. The local kind cluster is the **OSS / dry-run profile**. Measured
> capacity arithmetic and the reasoning are in
> [`docs/adr/014-azure-first-verification.md`](docs/adr/014-azure-first-verification.md).

[![Azure](https://img.shields.io/badge/Microsoft_Azure-Platform-0089D6?logo=microsoft-azure)](https://azure.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-AKS-326CE5?logo=kubernetes)](https://kubernetes.io/)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform)](https://terraform.io/)
[![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-EF7B4D?logo=argo)](https://argoproj.github.io/cd/)

This repository is the central infrastructure blueprint for a shared Azure Kubernetes platform designed to run multiple portfolio workloads (like the Flash-Sale backend). It demonstrates **Platform Engineering**, **GitOps**, and **SRE** principles applied to Azure.

*Note: This project is currently in the "Blueprint" phase, following an evidence-gated roadmap towards live provisioning.*

> ### Read this before anything else
>
> **Status is in transition. Read this before believing any headline claim.**
>
> **Applied to Azure, once, successfully.** Phase 7A.1 (system pool) and 7A.2
> (temporary user pool + Workload Identity proof) were both applied on
> 2026-09-21 and passed all 19 runtime gates — including private ACR pull by
> digest, federated token exchange, and a full teardown. That evidence is real
> and is in [`docs/evidence/phase7a/`](docs/evidence/phase7a/). The earlier
> claim on this page that "no cluster has ever been successfully applied" was
> **false** and has been removed.
>
> **What has not happened yet:** no persistent cluster, no CI, no HPA, no
> enforced NetworkPolicy, no SLO history. Those are the open items, tracked in
> [`tasks/current.md`](tasks/current.md).
>
> **Where verification now happens:** a real AKS cluster is the proof surface;
> the local kind cluster is the OSS / dry-run profile. That decision and its
> measured capacity arithmetic are in
> [`docs/adr/014-azure-first-verification.md`](docs/adr/014-azure-first-verification.md).
> Any result measured on kind is labelled `PRE_AZURE_DRY_RUN` and is **not**
> Azure evidence.

## 📐 Architecture & Platform Model

The platform strictly separates infrastructure provisioning from application deployment to establish a clear ownership model:

1. **Terraform (Infrastructure):** Manages the Azure boundaries for the platform itself (AKS cluster, node pools, networking foundation). Active roots and rules: [`terraform/README.md`](terraform/README.md). Application infrastructure (ACR, Service Bus, storage) lives with the owning workload repo.

2. **Bootstrap script (Platform Components):** `scripts/bootstrap.sh` installs Argo CD (upstream install manifest) and KEDA (upstream `kedacore/keda` Helm chart) into an already-provisioned cluster. There is **no Helm chart in this repo** (KEDA and Argo CD are consumed as upstream artifacts), and **no Ingress Controller and no external-secrets manifest exist anywhere in this repository** — those are not implemented here. Two further honest caveats: `scripts/bootstrap.sh:38` applies `gitops/argocd/application.yaml`, which exists in this repo only as `gitops/argocd/application.yaml.disabled`, so step 5/5 does not run as written; and the `TriggerAuthentication` Secret it applies is created out-of-band in a later phase, not by anything in this repo (`kubernetes/keda-trigger-auth.yaml:1-5`).
3. **Argo CD (GitOps):** Reconciles the desired application state from Git directly into the cluster, providing self-healing and drift detection.

## 🚀 Key Platform Features — as actually proven

Each line states its evidence, and names the environment it ran in. Nothing here
is a design intention presented as a result.

### Proven on real AKS (`AZURE_VALIDATION`, 2026-09-21, cluster destroyed after)

- **Cost-safe AKS foundation:** system pool with `only_critical_addons_enabled`
  (the `CriticalAddonsOnly=true:NoSchedule` taint), OIDC issuer, Workload
  Identity enabled, managed node provisioning set to `Manual`.
  → [`evidence/phase7a/system-foundation-PASS.md`](docs/evidence/phase7a/system-foundation-PASS.md)
- **User-pool isolation at runtime:** application workloads landed only on the
  user pool, nothing on the system pool.
  → [`evidence/phase7a/user-pool-placement-PASS.md`](docs/evidence/phase7a/user-pool-placement-PASS.md)
- **Private ACR pull, no `imagePullSecret`:** image pulled by digest using the
  kubelet's managed identity with `AcrPull`, spec left empty.
  → [`evidence/phase7a/private-acr-pull-PASS.md`](docs/evidence/phase7a/private-acr-pull-PASS.md)
- **Workload Identity token exchange:** ServiceAccount → federated credential →
  UAMI → Entra token → scoped `Reader` read, with no secret anywhere. Plus the
  negative control: the UAMI, FIC and proof namespace were deleted and access
  re-verified as gone.
  → [`evidence/phase7a/workload-identity-runtime-PASS.md`](docs/evidence/phase7a/workload-identity-runtime-PASS.md)
- **Clean teardown:** cluster stopped, temporary pool and all proof identities
  deleted, quota released, ≈ $0.20 compute. 19/19 gates PASS.
  → [`evidence/phase7a/phase7a-FINAL-PASS.md`](docs/evidence/phase7a/phase7a-FINAL-PASS.md)

### Proven on local kind (`PRE_AZURE_DRY_RUN`, not Azure evidence)

- **GitOps authority + rollback:** Argo CD v3.5.3 reconciled Git → cluster, and a
  `git revert` produced a rollback. Includes the drift case (manual
  `kubectl scale` detected as `OutOfSync`, then reconciled).
  → [`evidence/local-platform/l9-gitops-PASS.md`](docs/evidence/local-platform/l9-gitops-PASS.md)
- **North-south via Gateway API:** Envoy Gateway v1.9.1 sharing one gateway
  across isolated namespaces. ingress-nginx is retired upstream and is
  deliberately not used.
  → [`evidence/local-platform/l8-shared-gateway-PASS.md`](docs/evidence/local-platform/l8-shared-gateway-PASS.md)
- **Metrics, dashboards and a real alert cycle:** Prometheus + Grafana 91.5.0,
  14 scrape jobs, Git-provisioned dashboards, and one PrometheusRule that
  genuinely fired at `15:33:25Z` and resolved at `15:35:17Z`.
  → [`evidence/local-platform/l10-observability-PASS.md`](docs/evidence/local-platform/l10-observability-PASS.md)

### Defined in Terraform, not yet proven at runtime

- **Cluster Autoscaler and a persistent user pool.** The 7A user pool was
  temporary and was deleted during teardown; no scale-out was ever observed.
- **Key Vault access from a pod.** The identity chain was proven, but not a pod
  performing a secret read against a real vault.
- **Cilium-enforced NetworkPolicy.** `network_policy = "azure"` is set in
  Terraform; no policy has been enforced by an observed deny.

### Known inconsistencies, stated rather than hidden

- `kubernetes/order-worker.yaml` injects `ConnectionStrings__ServiceBus` from a
  Secret, while `kubernetes/keda-autoscaler.yaml` scales on a **RabbitMQ**
  `QueueLength` trigger. These two halves disagree. Both belong to the
  FlashSale repo's concerns and are being superseded, not extended.
- `scripts/bootstrap.sh:38` applies `gitops/argocd/application.yaml`, which only
  exists here as `application.yaml.disabled`, so step 5/5 cannot run as written.
- The `TriggerAuthentication` Secret that `bootstrap.sh:30` applies is created
  out-of-band, not by anything in this repo.

## 🗺️ Where the work actually stands

This README is a narrative only — it deliberately does **not** carry a live
phase checklist. The single source of truth for execution state is:

→ [`tasks/current.md`](tasks/current.md) — current phase, gates, and STOP conditions
→ [`docs/engineering/CURRENT_STATE.md`](docs/engineering/CURRENT_STATE.md) — the live engineering checkpoint for the next session
→ [`plans/`](plans/) — dated planning/decision documents (historical)
→ [`docs/evidence/`](docs/evidence/) — sanitized per-phase evidence (plans, cost, apply reports)
→ [`docs/adr/`](docs/adr/) — architecture decision records. ADR-012 (AKS foundation cost-safe design), ADR-013 (kind runtime, superseded in part), ADR-014 (Azure-first verification, active)
→ [`local/kind/`](local/kind/) — the **OSS / dry-run profile**, not the proof surface

As of 2026-10-02 this repo is in **Phase A–C of Execution Wave 1** under Cost
Safety Mode: documentation repaired, CI being built, Azure identity and ACR being
established. AKS was applied successfully once and is currently stopped and
destroyed. Read `tasks/current.md` before touching anything.

