# AKS / SRE Platform Blueprint (In Progress)

[![Azure](https://img.shields.io/badge/Microsoft_Azure-Platform-0089D6?logo=microsoft-azure)](https://azure.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-AKS-326CE5?logo=kubernetes)](https://kubernetes.io/)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform)](https://terraform.io/)
[![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-EF7B4D?logo=argo)](https://argoproj.github.io/cd/)

This repository is the central infrastructure blueprint for a shared Azure Kubernetes platform designed to run multiple portfolio workloads (like the Flash-Sale backend). It demonstrates **Platform Engineering**, **GitOps**, and **SRE** principles applied to Azure.

*Note: This project is currently in the "Blueprint" phase, following an evidence-gated roadmap towards live provisioning.*

> ### Read this before anything else
>
> **This repository is not a working platform, and no cluster has ever been
> successfully applied from it.** The authoritative status is in
> `tasks/current.md`.
>
> There is also **no CI and no automated testing of any kind**: this repo has no
> `.github/` directory, no commit-triggered workflow, and no test suite. Nothing
> here is verified automatically. Read it as honest coursework / design
> documentation, not as deployed infrastructure.

## 📐 Architecture & Platform Model

The platform strictly separates infrastructure provisioning from application deployment to establish a clear ownership model:

1. **Terraform (Infrastructure):** Manages the Azure boundaries for the platform itself (AKS cluster, node pools, networking foundation). Active roots and rules: [`terraform/README.md`](terraform/README.md). Application infrastructure (ACR, Service Bus, storage) lives with the owning workload repo.

2. **Bootstrap script (Platform Components):** `scripts/bootstrap.sh` installs Argo CD (upstream install manifest) and KEDA (upstream `kedacore/keda` Helm chart) into an already-provisioned cluster. There is **no Helm chart in this repo** (KEDA and Argo CD are consumed as upstream artifacts), and **no Ingress Controller and no external-secrets manifest exist anywhere in this repository** — those are not implemented here. Two further honest caveats: `scripts/bootstrap.sh:38` applies `gitops/argocd/application.yaml`, which exists in this repo only as `gitops/argocd/application.yaml.disabled`, so step 5/5 does not run as written; and the `TriggerAuthentication` Secret it applies is created out-of-band in a later phase, not by anything in this repo (`kubernetes/keda-trigger-auth.yaml:1-5`).
3. **Argo CD (GitOps):** Reconciles the desired application state from Git directly into the cluster, providing self-healing and drift detection.

## 🚀 Key Platform Features

- **Strategic Compute:** Defined a clear System vs. User node-pool strategy with specific taints/tolerations to protect control-plane addons from noisy neighbor application workloads.
- **Event-Driven Autoscaling (KEDA):** `kubernetes/keda-autoscaler.yaml` scales the `order-worker` Deployment between `minReplicaCount: 0` and `maxReplicaCount: 10` (lines 9-10) on a **RabbitMQ** `QueueLength` trigger for the `orders` queue (lines 12-15) — the `value: "50"` on line 16 is 50 queued messages per replica, not 50 replicas. There is **no Azure Service Bus ScaledObject in this repo**, and the two halves of this feature currently disagree: `kubernetes/order-worker.yaml:29-33` injects `ConnectionStrings__ServiceBus` from a `flashsale-secrets` Secret, so the workload is wired for Service Bus while the scaler watches RabbitMQ.
- **Resiliency Primitives (partial):** A `PodDisruptionBudget` for `order-api` is defined in `kubernetes/pod-disruption-budget.yaml`. Beyond that the original claim does not hold today: there is **no** `affinity`, `podAntiAffinity` or `topologySpreadConstraints` anywhere under `kubernetes/`, and **no** liveness, readiness or startup probes in any manifest there. Zone-spread scheduling is explicitly deferred to "Phase 10" (`terraform/aks-foundation/main.tf:36`).
- **Workload Identity:** Designed the security posture to eliminate static secrets (connection strings) in the cluster, utilizing Azure AD Workload Identity for seamless, credential-free access to Azure resources (Service Bus, Key Vault).

## 🗺️ Where the work actually stands

This README is a narrative only — it deliberately does **not** carry a live
phase checklist. The single source of truth for execution state is:

→ [`tasks/current.md`](tasks/current.md) — current phase, gates, and STOP conditions
→ [`plans/`](plans/) — dated planning/decision documents (historical)
→ [`docs/evidence/`](docs/evidence/) — sanitized per-phase evidence (plans, cost, apply reports)
→ [`docs/adr/`](docs/adr/) — architecture decision records (e.g. ADR-012, AKS foundation cost-safe design)
→ [`local/kind/`](local/kind/) — **local** portfolio platform cluster (kind), so work
   continues without Azure runtime spend

As of the last update this repo is in **Phase 7A (AKS foundation, quota
recovery)** under Cost Safety Mode: no cluster has been successfully applied
yet. Read `tasks/current.md` before touching anything.

