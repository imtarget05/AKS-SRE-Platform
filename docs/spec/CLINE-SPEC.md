# PROJECT SPEC — 03-AKS-SRE-Platform

## 1. Goal

Xây dựng platform AKS thể hiện năng lực:

- Azure
- AKS
- Terraform / IaC
- Kubernetes
- GitOps
- observability
- SRE
- autoscaling
- resilience
- security
- backup/disaster recovery
- cost awareness

Không thêm AI chỉ để tăng buzzword.

---

# 2. Target Architecture

```text
GitHub
  |
  v
CI
  |
  v
Container Registry
  |
  v
GitOps Repository
  |
  v
Argo CD
  |
  v
AKS
  |
  +-- Application Namespace
  +-- Observability
  +-- Ingress
  +-- Autoscaling
  +-- Policy/Security
```

Infrastructure via Terraform.

---

# 3. Required Capability Areas

## Infrastructure as Code

- resource group;
- networking;
- AKS;
- container registry;
- identities;
- secret integration where available;
- outputs;
- remote state strategy documented.

## Kubernetes

- deployment;
- service;
- ingress;
- config;
- secret reference;
- requests/limits;
- probes;
- PDB where justified;
- HPA.

## GitOps

- Argo CD;
- environment manifests;
- promotion strategy;
- rollback.

## Observability

- metrics;
- logs;
- dashboards;
- alerts;
- SLI/SLO.

## Security

- workload identity or secure alternative;
- RBAC;
- secret handling;
- image scanning;
- network policy if justified;
- pod security controls.

## Reliability

- node failure behavior;
- pod restart;
- scaling;
- rolling update;
- rollback.

## Backup / DR

Must document:

- application data;
- Kubernetes objects;
- persistent data;
- recovery objectives;
- restore drill.

---

# 4. SRE Requirements

Define one service SLO, example:

```text
Availability SLO: 99.9%
Latency SLI: p95 < 500ms
Error Rate: < 1%
```

Must show:

- measurement source;
- dashboard;
- alert threshold;
- runbook.

---

# 5. Cost Control

Document:

- Free control plane assumptions if applicable;
- node sizing;
- Spot usage tradeoff;
- autoscaling;
- shutdown strategy for portfolio environment;
- cost risks.

Never claim exact cost without actual current measurement.

---

# 6. Adaptive Business Architecture

Demonstrate:

```text
Low traffic
-> minimal capacity

Traffic spike
-> HPA
-> cluster autoscaling if configured

Spot eviction
-> workload rescheduled

Bad deployment
-> rollback
```

---

# 7. Phases

## Phase 0 — Audit
Current repo status and gaps.

## Phase 1 — Terraform Baseline
Network + AKS + ACR + identities.

## Phase 2 — Workload
Deploy real application.

## Phase 3 — GitOps
Argo CD and environment structure.

## Phase 4 — Observability
Metrics/logs/dashboard/alerts.

## Phase 5 — Reliability
HPA, probes, PDB, failure drills.

## Phase 6 — Security
RBAC, secret strategy, scanning/policies.

## Phase 7 — Backup / Restore
Realistic recovery plan and drill.

## Phase 8 — Cost / Architecture Documentation
Document scaling and business adaptation.

---

# 8. Demo Scenarios

1. Git commit triggers image build.
2. GitOps deploys change.
3. Failed health check blocks/rolls bad rollout.
4. Pod deleted -> recreated.
5. Load increases -> HPA reacts.
6. Alert fires for simulated error.
7. Restore workflow shown/documented.

---

# 9. Out of Scope

- AI feature unrelated to platform;
- too many managed Azure services without business need;
- fake chaos engineering;
- fake cost reports;
- pretending production SLA without evidence.

---

# 10. Definition of Done

- infra code is reproducible;
- application deployed;
- GitOps works;
- observability has actual signals;
- at least one SLO defined;
- scaling demonstrated;
- failure scenario demonstrated;
- secrets are handled safely;
- backup/recovery documented and tested to a realistic extent;
- architecture diagram + runbooks exist.
