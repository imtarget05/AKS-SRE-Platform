# Master Roadmap — CloudDevOpsPortfolio (2026-09-21, rev.2 mandatory 9–18)

Source of truth for sequencing. P01/P02 software+container+release ✅; rest is P03 live platform → packaging.
Rev.2 (2026-09-21, user directive): microservices/Saga/Payment/Kafka/Loki/Tempo/Service Mesh are
**MANDATORY completion (phases 9–13, then 14–18)**, NOT future-optional. Supersedes the rev.1
"out of scope" line. Full spec: `2026-09-21-microservices-mandatory-roadmap-9-to-18.md`.
Hard gate: no Phase 9+ before 7A→8 baseline green.

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
| 8 | Observability baseline | Prometheus+Grafana+alerts+SLO (no Loki/Tempo — Phase 12) | live metrics/alerts |
| 9 | Microservices decomposition | Order/Inventory/Payment/Saga/Worker, separate images + data ownership | ownership gates |
| 10 | Kafka event backbone | KRaft single-broker NON-HA, domain topics, outbox+inbox, idempotency | replay + dup-proof |
| 11 | Saga + Payment workflow | happy path + 4 failure paths, compensation + recovery | recovery gates |
| 12 | Full observability | Alloy + Loki + Tempo + OTel, end-to-end checkout trace | trace↔log correlation |
| 13 | Service mesh | Istio ambient, mTLS, authz allow/deny, latency measured | policy + overhead |
| 14 | Reliability | failure experiments + TTR (incl. Kafka/Saga/mesh/obs outage) | measured recovery |
| 15 | DR | rebuild + DB restore + RPO/RTO (saga state, GitOps/mesh config covered) | drill PASS |
| 16 | Scaling | KEDA (P01 worker + Kafka lag) + HPA (P02) measured | scale proven |
| 17 | Solution architecture | decision table (why Kafka/Saga/mesh/…) + profiles + triggers | documented |
| 18 | Packaging | READMEs, diagrams, demo, EVIDENCE.md, CV | interview-ready |

Milestones: 7F = deployable; 8 = strong interview-ready; 9–13 = distributed-systems differentiator; 14–18 = hardening + packaging.

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
8: Prometheus/Grafana/Alertmanager baseline (no Loki/Tempo — moved to 12), app+platform dashboards, ≥1 alert fire+resolve, SLI/SLO (hypothetical marked REFERENCE).
9: P01 monorepo decomposition — Order/Inventory/Payment services + Checkout.Saga + Fulfillment.Worker; separate images (`:<SHA>`), separate deploys, one PG instance with per-service schemas, no cross-service reads.
10: Kafka KRaft single-broker NON-HA, domain topics, transactional outbox + consumer inbox, at-least-once + idempotent consumers (dup ×5 → one transition proof).
11: Saga happy path + inventory-reject / payment-decline / payment-timeout / compensation-failure paths; durable saga state, idempotent commands, `MANUAL_INTERVENTION_REQUIRED` escape hatch.
12: Alloy collector → Prometheus/Loki/Tempo; single-traceId checkout across Order→Kafka→Saga→Inventory→Payment; structured logs; no public Loki.
13: Istio ambient (`istio.io/dataplane-mode: ambient`), ztunnel mTLS, AuthorizationPolicy allow/deny matrix, waypoint only on L7 demand, before/after latency numbers; ingress-nginx stays north-south.
14: controlled experiments incl. Kafka/Saga/payment/mesh/Loki/Tempo outages (obs outage must NOT break checkout) with Hypothesis→TTR incident files. 15: full rebuild drill with actual RPO/RTO + authoritative-vs-rebuildable ADR.
16: KEDA RabbitMQ queue (P01) + KEDA Kafka lag + HPA (P02); cluster autoscaler only after quota+approval. 17: decision table + 4 profiles conditional.
18: 3-repo narrative (build/productionize/operate), READMEs, diagrams, 10–15min distributed demo (push→Saga→trace→mTLS→compensation→rollback), EVIDENCE.md claim table, Sonar truthful (NOT enforced until CI gate real).

## Interview DoD chain

BUSINESS → P01 → CORRECTNESS → DATA PROTECTION → CONTAINERS → DEVSECOPS → RELEASE → ACR → TERRAFORM → AKS → ARGO CD → P01+P02 → OBS → MICROSERVICES → KAFKA → SAGA → TRACE (Loki/Tempo) → MESH → FAILURE → DR → KEDA/HPA → ARCHITECTURE. Each box: implemented? executed? verified? evidence? failure? cost? real-company change?
