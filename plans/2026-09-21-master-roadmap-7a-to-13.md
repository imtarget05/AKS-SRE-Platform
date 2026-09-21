# Master Roadmap — CloudDevOpsPortfolio (2026-09-21)

Source of truth for sequencing. P01/P02 software+container+release ✅; rest is P03 live platform → packaging.
Out of scope for completion: microservices/Saga/Payment/Kafka/Loki/Tempo/Service Mesh.

## Starting point

- P01 FlashSale-Backend: backend + correctness + container + release ✅
- P02 Productionized-LegacyApp: productionization + security gate + release ✅
- P03 AKS-SRE-Platform: P0 structural safety ✅, 7A apply#1 ⚠️ BLOCKED (DASv5 quota), D4s_v6 recovery ← CURRENT

## Phase table

| Phase | Goal | Output | Gate |
|---|---|---|---|
| 7A.1 | AKS system foundation (D4s_v6) | live AKS + 2 sys nodes + ACR RBAC | Nodes Ready |
| 7A.2 | User-pool proof | private ACR pull + WI proof, pool deleted | runtime proof |
| 7B | Platform bootstrap | user pool + ingress-nginx + Argo CD | Platform Healthy |
| 7C | Deploy P01 | FlashSale E2E on AKS | Order Completed |
| 7D | Deploy P02 | LegacyApp via shared ingress | Healthy/Synced |
| 7E | GitOps E2E | CI→ACR→GitOps→Argo + rollback both | proven |
| 7F | Cost & lifecycle | start/stop/status + quota scripts + drill | stop/start proven |
| DP checkpoint | Data protection closure | off-host backup + restore artifacts | required before destructive tests |
| 8 | Observability | Prometheus+Grafana+alerts+SLO | live metrics/alerts |
| 9 | Reliability | failure experiments + TTR | measured recovery |
| 10 | DR | rebuild + DB restore + RPO/RTO | drill PASS |
| 11 | Scaling | KEDA (P01 worker) + HPA (P02) measured | scale proven |
| 12 | Solution architecture | 4 profiles + tradeoffs + triggers | documented |
| 13 | Packaging | READMEs, 6 diagrams, demo, EVIDENCE.md, CV | interview-ready |

Milestones: 7F = deployable; 8 = strong interview-ready; 9–13 = differentiator.

## 7A.1 (this task — APPROVED for system-only apply)

Flow: fresh quota (Dsv6≥8, regional≥8) → refresh → SKU D4s_v6 only → saved plan 2/0/0 → apply exact plan →
verify (2 Ready, kube-system healthy, OIDC+WI, AcrPull, no apps) → cost inventory → `az aks stop` → `system-foundation-PASS.md` → STOP (no 7A.2).
Limits: RG+AKS+role only. No user pool/proofs/Argo/ingress/P01/P02.

## 7A.2+ (locked, separate approvals)

7A.2: temp D2s_v6 pool (10/10) → placement + private pull (`legacy-app:<SHA>`, no secret) + WI harmless read → delete pool → 8/10 → stop.
7B: request quota ~16 first; 1 ingress-nginx, Argo CD (port-forward), namespaces argocd/ingress-nginx/flashsale/legacyapp(+monitoring reserved).
7C: P01 via GitOps (PG stateful+PVC, Redis reconstructable, RabbitMQ durable+Secret, PreSync migration Job, Kafka OFF) → E2E order proof.
7D: P02 second workload (non-root 1000, SHA pin, shared ingress).
7E: forward deploy + revert rollback per project, artifact traceability (source=ACR=GitOps=pod).
7F: lifecycle scripts + real stop/start drill.
DP: off-host Blob backup + clean restore + rabbit/redis rebuild + remote state — gate before destructive tests.
8: Prometheus/Grafana/Alertmanager (no Loki/Tempo), app+platform dashboards, ≥1 alert fire+resolve, SLI/SLO (hypothetical marked REFERENCE).
9: 8 controlled experiments with Hypothesis→TTR incident files. 10: full rebuild drill with actual RPO/RTO.
11: KEDA RabbitMQ queue (P01) + HPA (P02); cluster autoscaler only after quota+approval. 12: 4 profiles conditional.
13: 3-repo narrative (build/productionize/operate), READMEs, 6 diagrams, 5–10min demo, EVIDENCE.md claim table, Sonar truthful (NOT enforced until CI gate real).

## Interview DoD chain

BUSINESS → P01 → CORRECTNESS → DATA PROTECTION → CONTAINERS → DEVSECOPS → RELEASE → ACR → TERRAFORM → AKS → ARGO CD → P01+P02 → OBS → FAILURE → DR → KEDA/HPA → ARCHITECTURE. Each box: implemented? executed? verified? evidence? failure? cost? real-company change?
