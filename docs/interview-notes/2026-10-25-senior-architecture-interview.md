# Senior Engineering Interview Guide — Portfolio Architecture & Live Incidents

**Target Roles:** Senior Software Engineer / Backend Engineer / Cloud & DevOps Engineer / SRE  
**Core Platform:** Azure Flash-Sale Order Reliability Platform & Quản Lý Kho Operations  
**Date:** 2026-10-25  
**Evidence Grounding:** All metrics, logs, and incidents are grounded in live telemetry from Microsoft Azure AKS (`aks-portfolio-dev`), Cloudflare Pages, and PostgreSQL 16.

---

## 1. System Architecture & High-Level Design

### Business Problem
A retailer holds flash sales with limited inventory (e.g. 5–10 units) and high concurrent burst traffic (thousands of shoppers per second). The system must guarantee:
1. **Zero overselling** (stock conservation invariant: $\text{Sold} + \text{Remaining} == \text{Initial}$).
2. **Idempotency** on client retries and network timeouts.
3. **Resilience** against database overload and messaging broker outages.
4. **Data Isolation** between high-concurrency flash sales and enterprise warehouse accounting.

### Clean Architecture & Layering
```text
Domain  ←  Application  ←  Infrastructure  ←  Presentation (Composition Roots)
```
- **Domain (`FlashSale.Domain` / `OpsBridge.Domain`):** Pure C# entities (`Order`, `Product`, `StockReservation`), domain exceptions, invariants. Zero third-party dependencies (no EF Core, no Redis, no ASP.NET Core).
- **Application (`FlashSale.Application` / `OpsBridge.Application`):** Use cases (`SubmitOrderUseCase`, `ProcessOrderUseCase`) and ports (`IOrderRepository`, `IOrderReadModel`, `IStockReservationGateway`, `IOrderQueueProducer`).
- **Infrastructure (`FlashSale.Infrastructure` / `OpsBridge.Infrastructure`):** Adapters implementing ports (`PostgresOrderRepository`, `RedisStockGateway`, `RabbitMqDomainEventPublisher`, `TransactionalOutboxRepository`).
- **Presentation (`Order.Api`, `Order.Worker`, `OpsBridge.Api`):** Thin composition roots in ASP.NET Core, mapping endpoints to use cases and DI wiring.

---

## 2. Key Architectural Decisions & Solution Comparisons

### A. Preventing Overselling Under Concurrency
- **Option 1 — Pessimistic Row Lock (`SELECT FOR UPDATE`):**
  - *Mechanism:* Lock the database product row for the duration of the checkout transaction.
  - *Trade-off:* Serializes transactions at the DB engine; causes high lock contention, connection pool exhaustion, and poor throughput under 1,000+ RPS.
- **Option 2 — Optimistic Locking (Row Version CAS):**
  - *Mechanism:* Check version timestamp on UPDATE; abort transaction if version changed.
  - *Trade-off:* High abort and rollback rate under hot-spot contention (95%+ retries fail).
- **Option 3 — Atomic Conditional Update + Fast-Fail Cache (SELECTED):**
  - *Mechanism:* Fast-fail pre-check in Redis via atomic decrement (`DECRBY`). If Redis stock $\le 0$, reject immediately (HTTP 409) in $<2\text{ms}$. If approved, database performs an atomic conditional update:
    $$\text{UPDATE "Products" SET "AvailableStock" = "AvailableStock" - @qty WHERE "Id" = @id AND "AvailableStock" } \ge \text{ @qty}$$
  - *Verification:* Tested under 200 concurrent requests for 10 items. Committed orders $= 10$, remaining stock $= 0$, zero oversell.

### B. Distributed Messaging & Reliability (At-Least-Once Delivery)
- **Option 1 — Direct Publish from API to Broker:**
  - *Risk:* Dual-write problem. If database commits order but broker network fails, the event is permanently lost. If broker publish succeeds but database rollback occurs, a phantom order is processed.
- **Option 2 — Transactional Outbox Pattern (SELECTED):**
  - *Mechanism:* The order record and the domain event are written to the database (`Orders` and `OutboxMessages`) in the **same atomic database transaction**.
  - A background publisher (`Order.Worker`) polls pending outbox messages, publishes to RabbitMQ/Kafka, and marks them dispatched.
  - *Idempotency on Consumer:* Consumer implements an Inbox pattern with `IdempotencyKey`. Duplicate messages return cached outcomes without reprocessing.

### C. Public Edge Architecture: Cloudflare to Azure Origin
- **Option 1 — Cloudflare Tunnel (`cloudflared`):** Requires custom domains with CNAME routing; unstable on ephemeral demo clusters without dedicated DNS zones.
- **Option 2 — Direct Azure Origin Ingress:** Bypasses Cloudflare edge DDoS protection, rate limits, and WAF rules.
- **Option 3 — Cloudflare Worker API Edge + Mutual TLS (mTLS) to Azure Envoy Gateway (SELECTED):**
  - Cloudflare Pages hosts static frontends.
  - Worker on `workers.dev` accepts requests, applies rate limiting (`RATE_ORDER`, `RATE_AUTH`), strips spoofed headers, and forwards to Azure Gateway over mTLS.
  - Azure Envoy Gateway validates the Cloudflare client certificate via `ClientTrafficPolicy`. Requests lacking the certificate are rejected at TLS handshake (TCP reset / alert 42).

---

## 3. Real Production Incidents & Root Cause Analysis

### Incident 1: Pod Scheduling Starvation (Insufficient CPU / Too Many Pods)
- **Observed Problem:** Job `order-migrate` stuck in `Pending` for >90 minutes on AKS.
- **Root Cause:** Node 0 reached Azure CNI 30-pod limit. Node 1 had 1820m/1900m CPU requested (95% saturation). Remaining 80m CPU was insufficient for migration pod's 100m request.
- **Investigation:** `kubectl describe pod` revealed scheduler refusal. Node resource allocation audit showed unused frontend pods holding requests.
- **Solution:** Scaled unused components to 0 and right-sized replicas. CPU requests dropped to 1720m (90%), allowing migration to schedule and complete in 28 seconds.
- **Interview Takeaway:** Distinguish between actual CPU *utilization* (low) vs *requests* (high). Kubernetes scheduler only considers requests when evaluating placement.

### Incident 2: RabbitMQ CrashLoopBackOff (Erlang Cookie & Startup Probe)
- **Observed Problem:** RabbitMQ stateful pod failing health checks and restarting repeatedly.
- **Root Cause:** Volume mount overrode `/var/lib/rabbitmq` with root permissions, preventing RabbitMQ (UID 999) from setting `chmod 400` on `.erlang.cookie`. Startup latency under disk I/O exceeded 1s liveness probe timeout.
- **Solution:** Added an `initContainer` to `chown 999:999` and `chmod 400`, and increased probe timeout to 5s.

### Incident 3: Startup Dependency Race Condition (API vs PostgreSQL Cold-Boot)
- **Observed Problem:** `payment-service` suffered 7 restarts upon cluster boot.
- **Root Cause:** Kubernetes started all pods in parallel. API pods attempted database connection before PostgreSQL completed WAL replay.
- **Solution:** Configured exponential backoff retry in EF Core connection pool and gated traffic using Kubernetes readiness probes (`/health/ready`).

---

## 4. Live Failure Drills & Measurements

| Drill ID | Failure Injected | System Response | Recovery Time (RTO) | Data Integrity (RPO) |
|---|---|---|---|---|
| **INC-D01** | Killed live `order-api` pod | ReplicaSet scheduled new pod; alternative replica handled traffic | **7 seconds** | Zero dropped requests |
| **INC-D02** | Synthetic order duplicate retry | First request $\to$ HTTP 202; retry with same key $\to$ HTTP 409 | **Instantaneous** | Exactly 1 DB row, 0 double orders |
| **INC-D03** | Missing JWT / Unauthenticated API call | `order-api` returned HTTP 401 Unauthorized | **Instantaneous** | Zero data leaked |

---

## 5. Technical Questions & Senior Answers

**Q1: How do you handle database migration in a zero-downtime deployment?**  
*Answer:* Never run EF Core or Alembic migrations inside the application container's startup code (`Program.cs` or `main.py`). In a multi-replica deployment (`replicas: 2+`), multiple pods race to execute `MigrateAsync()`, which can lead to deadlocks or corrupted schema locks. Instead, use a single-shot Kubernetes PreSync Job (`order-migrate`) with bounded retry (`backoffLimit: 3`) and strict resource limits. The application pods only roll after the migration Job completes successfully. Furthermore, migrations must follow the **Expand/Contract pattern**: add nullable columns first, deploy new code, backfill data, and only remove old columns in a subsequent release.

**Q2: What is the difference between At-Least-Once and Exactly-Once in distributed systems?**  
*Answer:* In real distributed systems with network unreliability, physical message brokers (RabbitMQ, Kafka, Azure Service Bus) provide **at-least-once delivery**. Transient network timeouts between producer and broker or consumer and broker can result in duplicate deliveries. True "exactly-once" processing is achieved at the **application boundary** by combining at-least-once transport with **idempotent consumers**:
1. Every event carries an immutable `IdempotencyKey`.
2. The consumer checks an `Inbox` table in the same database transaction as the business operation.
3. If the key already exists, the consumer acknowledges the message and returns the previously computed outcome without side effects.
