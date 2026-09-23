# AKS / SRE Platform Blueprint (In Progress)

[![Azure](https://img.shields.io/badge/Microsoft_Azure-Platform-0089D6?logo=microsoft-azure)](https://azure.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-AKS-326CE5?logo=kubernetes)](https://kubernetes.io/)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform)](https://terraform.io/)
[![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-EF7B4D?logo=argo)](https://argoproj.github.io/cd/)

This repository is the central infrastructure blueprint for a shared Azure Kubernetes platform designed to run multiple portfolio workloads (like the Flash-Sale backend). It demonstrates **Platform Engineering**, **GitOps**, and **SRE** principles applied to Azure.

*Note: This project is currently in the "Blueprint" phase, following an evidence-gated roadmap towards live provisioning.*

## 📐 Architecture & Platform Model

The platform strictly separates infrastructure provisioning from application deployment to establish a clear ownership model:

1. **Terraform (Infrastructure):** Manages the Azure boundaries for the platform itself (AKS cluster, node pools, networking foundation). Active roots and rules: [`terraform/README.md`](terraform/README.md). Application infrastructure (ACR, Service Bus, storage) lives with the owning workload repo.

2. **Helm / Bootstrap (Platform Components):** Manages foundational cluster services (Ingress Controllers, KEDA, external-secrets).
3. **Argo CD (GitOps):** Reconciles the desired application state from Git directly into the cluster, providing self-healing and drift detection.

## 🚀 Key Platform Features

- **Strategic Compute:** Defined a clear System vs. User node-pool strategy with specific taints/tolerations to protect control-plane addons from noisy neighbor application workloads.
- **Event-Driven Autoscaling (KEDA):** Designed KEDA ScaledObjects to dynamically scale background workers (0 to 50) based on Azure Service Bus queue depth, decoupling scaling from simple CPU metrics.
- **Resiliency Primitives:** Defined `PodDisruptionBudgets` (PDBs), anti-affinity rules, and liveness/readiness probes to ensure application survivability during cluster upgrades or node failures.
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

