# Microservices Mandatory Roadmap — Focus Plan (2026-09-21)

> Created via repo-harness plan capture (direct timestamped plan under `plans/`;
> `repo-harness run new-plan` helper is interactive-only, so this file is the
> equivalent artifact). Source: user directive 2026-09-21 — microservices,
> Payment Service, Saga, Kafka, Loki, Tempo, Service Mesh move from
> "future optional" to **mandatory completion**, sequenced AFTER baseline.

## 1. Goal

Extend the master roadmap (`plans/2026-09-21-master-roadmap-7a-to-13.md`,
which currently marks microservices/Saga/Payment/Kafka/Loki/Tempo/Service Mesh
as **out of scope**) into a mandatory phase chain:

```text
CURRENT → 7A → 7B → 7C → 7D → 7E → 7F → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → DONE
```

Hard sequencing rule: **no Phase 9+ work lands before baseline
AKS + GitOps + basic observability (7A–8) is green**. The story must stay
tellable in interviews: modular baseline first, measured, then bounded-context
extraction, then Kafka/Saga only when distributed consistency becomes a real
problem, then tracing/mesh once service-to-service complexity justifies them.

## 2. Current repo state (verified 2026-09-21)

- `tasks/current.md` (AKS-SRE-Platform): active goal Phase 7A.1 APPLY
  (APPROVED system-only, D4s_v6). Preflight fresh PASS; STOP gate holds for
  everything beyond the approved system-only apply (7A.2 locked).
- `tasks/current.md` (FlashSale-Backend): Phases 1–5 done, container/IaC/CI-CD
  done; Next = OTel→App Insights, Key Vault CSI, chaos experiment.
- `.ai/harness/handoff/resume.md`: **absent** in both repos (no pending handoff
  state; `tasks/current.md` files are the authority).
- Master roadmap still says microservices et al. are out of scope — this plan
  is the change request that supersedes that line.
- No microservices/Kafka/Saga/Loki/Tempo/mesh code exists yet (correct per
  sequencing — nothing to revert).

## 3. Work breakdown (mandatory phases)

### Phase 9 — Microservices evolution (P01 monorepo, separate runtimes)

- Extract bounded contexts in `FlashSale-Backend/`: `Order.Api/Application/
  Infrastructure`, `Inventory.*`, `Payment.*` (with `FakePaymentProvider`:
  deterministic fixtures, e.g. amount `...01`→success, `...02`→decline,
  `...03`→timeout), `Checkout.Saga`, `Fulfillment.Worker`.
- Data: one PostgreSQL instance, separate databases/schemas per service;
  **no cross-service table reads** (API or event only).
- Containers: `order/inventory/payment-service:<SHA>`, `checkout-saga:<SHA>`,
  `fulfillment-worker:<SHA>` (no `latest`).
- Gate: Order cannot mutate Inventory DB; payment owns its state; separate
  build/deploy/health endpoints; behavior preserved.

### Phase 10 — Kafka event backbone

- KRaft, single broker, labeled `NON-HA PORTFOLIO MODE`. Domain topics
  (`orders/inventory/payments.events` + `checkout.commands/events`), eventType
  inside schema (no topic explosion).
- Transactional Outbox (business row + outbox row in one local transaction,
  relay to Kafka) + consumer Inbox/dedup (`ProcessedMessages` keyed by
  MessageId). Claim only at-least-once + idempotent consumers + outbox.
- Evidence: `docs/adr/013-kafka-event-backbone.md`, `docs/evidence/kafka/`
  (broker/topics/producer/consumer/duplicate-delivery/outbox/replay),
  incl. broker-down→outbox-pending→recover→deliver proof and same-event-×5 →
  one state transition.

### Phase 11 — Payment + Saga distributed transaction

- Happy path + 4 failure paths (inventory reject, payment decline→release
  inventory, payment timeout→idempotent retry, compensation failure→retry/
  `MANUAL_INTERVENTION_REQUIRED`). No distributed DB transaction; durable saga
  state (`SagaId/OrderId/CurrentStep/InventoryStatus/PaymentStatus/
  CompensationStatus/Version/UpdatedAt`); idempotent commands.
- Evidence: `docs/evidence/saga/` (7 files: happy-path, inventory-reject,
  payment-decline, payment-timeout, duplicate-command, compensation,
  compensation-failure).

### Phase 12 — Loki + Tempo + OpenTelemetry (Grafana Alloy collector)

- Metrics→Prometheus, Logs→Loki, Traces→Tempo, all in Grafana. OTLP pipeline
  from .NET services, Node LegacyApp, later Istio. One `traceId` across full
  checkout; structured logs (`timestamp/level/service/traceId/spanId/orderId/
  sagaId/eventType/message`); no secrets in logs; **no public Loki endpoint**.
- Evidence: `docs/evidence/observability/` (logs-loki, traces-tempo,
  trace-log-correlation, checkout-distributed-trace).

### Phase 13 — Service Mesh (Istio Ambient)

- `flashsale` namespace labeled `istio.io/dataplane-mode: ambient`; ztunnel
  L4 mTLS + AuthorizationPolicy (`Order/Saga→Inventory/Payment ALLOW`,
  `LegacyApp→Payment DENY`, cross-DB DENY); waypoint only where L7 needed;
  keep ingress-nginx north-south. Measure latency before/after (no-mesh vs
  ambient L4 vs waypoint L7).
- Evidence: `docs/evidence/service-mesh/` (7 files).

### Phases 14–18 — Harden, recover, scale, narrate, package

- 14 Reliability: Kafka/Saga/payment/mesh/Loki/Tempo failure tests; observability
  outage must NOT break checkout; `docs/incidents/INC-007…010`.
- 15 DR: authoritative vs rebuildable ADR (DBs+saga state backed up; Kafka
  messages rebuildable by policy); GitOps/mesh/observability config covered.
- 16 Scaling: KEDA on Kafka consumer lag (+ existing RabbitMQ depth), HPA on
  HTTP services; burst→lag→scale→drain→down drill.
- 17 Architecture: decision table (why microservices/Kafka/RabbitMQ/Saga/
  outbox/Loki/Tempo/ambient) + comparison narratives.
- 18 Packaging: 10–15 min end-to-end demo script (push→CI→ACR→GitOps→ArgoCD→
  checkout→Kafka→Saga→Grafana/Tempo/Loki→mTLS→payment-failure compensation→
  rollback).

Kafka vs RabbitMQ role split (enforced everywhere): Kafka = durable
domain-event backbone/integration events/replay; RabbitMQ = task/job queue to
fulfillment worker. Never interchangeable.

## 4. Verification

- Per-phase gates as listed above (Phase 9 gate 7 checks; Phase 11 gate 7
  checks; Phase 12 gate 5 checks; Phase 13 latency before/after numbers).
- Harness hygiene: `repo-harness run check-task-workflow` clean after each
  `tasks/current.md` update; no raw `.tfplan` in git; ADRs for Kafka,
  DR-authoritative, mesh-mode choices; incident files for failure drills.
- No phase claims DONE without its evidence directory populated with real
  command outputs (never fabricated numbers).

## 5. Acceptance criteria (Definition of Done delta)

Project is NOT complete until, in addition to the existing DoD, evidence is
green for: Microservices, Inventory Service, Payment Service, Kafka,
Transactional Outbox/Inbox, Saga + compensation, Loki, Tempo, OpenTelemetry,
Istio Ambient Service Mesh — plus Reliability, DR, Scaling, Architecture
review, Portfolio packaging on the final architecture (not the old modular one).

## 6. Risks / rollback

- Risk: scope creep pulls Phase 9+ into 7A–8 work. Mitigation: this plan's
  sequencing rule is a hard gate; any 9+ PR before Phase 8 green is rejected.
- Risk: Azure credit burn (extra brokers/pools). Mitigation: single-broker
  Kafka NON-HA, one PG instance with separate schemas, waypoint only on demand.
- Rollback: this plan changes docs/plans/tasks only — revert the two
  `tasks/current.md` edits + delete this file. No infra touched, no apply
  authorized by this plan (7A STOP gate unchanged).
