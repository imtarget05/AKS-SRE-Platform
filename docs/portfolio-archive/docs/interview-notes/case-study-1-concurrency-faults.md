# Case Study 1: Concurrency Under High Contention & Outbox Fault Tolerance

**Role Target:** Senior Software Engineer (Backend / Distributed Systems)  
**System:** `services/opsbridge-flashsale` (.NET 10 / ASP.NET Core / PostgreSQL 15 / Redis 7 / RabbitMQ 3)  
**Evidence Artifacts:**
- Concurrency 50/10 Harness: `docs/evidence/2026-10-23-50-contenders-10-units.md`
- Outbox Crash Window & Compensation: `docs/evidence/kind-golden-path-rollback-evidence.md`
- Test Suites: `FlashSale.IntegrationTests` (87/87 pass), `FlashSale.UnitTests` (192/192 pass)

---

## 1. Business Problem
A retailer holds a flash sale with limited stock (e.g., 10 units of a high-demand item). 50 to 1,000 customers submit purchase orders within milliseconds.
Naive implementations suffer from:
1. **Overselling (Race Conditions):** Read-then-write anomalies allocate more inventory than available, causing expensive refunds and brand damage.
2. **Database Saturation:** Thousands of concurrent connection pool requests overwhelm PostgreSQL with row-level contention and lock timeouts.
3. **Dual-Write Inconsistency & Message Loss:** If stock reservation succeeds in the database but the message broker rejects the message or the worker crashes before emitting domain events, inventory is permanently orphaned.

---

## 2. Technical Architecture & Engineering Decisions

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as Order.Api (.NET 10)
    participant Redis as Redis 7 (Fast-Fail Cache)
    participant DB as PostgreSQL 15 (Source of Truth)
    participant Queue as RabbitMQ 3 (At-least-once Queue)
    participant Worker as Order.Worker

    Client->>API: POST /api/orders (Idempotency-Key: K, Qty: 1)
    API->>Redis: Atomic DECRBY / Lua Reservation
    alt Out of Stock in Redis
        Redis-->>API: Stock < 0
        API->>Redis: Atomic INCRBY (Revert)
        API-->>Client: 409 Conflict ("Out of stock")
    else Stock Available in Redis
        API->>DB: Check Idempotency Key (Read Model)
        API->>Queue: Publish OrderPlacedEvent (RabbitMQ)
        API-->>Client: 202 Accepted (Status: "processing")
        Queue->>Worker: Consume Order
        Worker->>DB: BEGIN TX; SELECT FOR UPDATE (PostgreSQL Stock); INSERT Order; INSERT Outbox; COMMIT TX
        Worker->>DB: Dispatch Outbox -> Publish OrderCompletedEvent
    end
```

### Decision A: Fast-Fail Cache (Redis) vs. Strict Persistence (PostgreSQL)
- **Problem:** Database cannot withstand 10,000 unthrottled concurrent row locks per second.
- **Solution:** Two-tiered inventory reservation.
  - Layer 1 (Fast-Fail): Redis atomic decrement with Lua script rejects excess traffic at line-rate in sub-millisecond time.
  - Layer 2 (Financial Truth): PostgreSQL row locks (`SELECT ... FOR UPDATE`) in an isolated transaction enforce exact zero-oversell invariant.
- **Trade-off:** Redis drift is possible if a worker crashes before DB commit. Reconciled via periodic compensating sweeps and TTL leases.

### Decision B: Transactional Outbox Pattern & Crash Windows
- **Problem:** Writing to PostgreSQL and RabbitMQ in two non-atomic calls creates a dual-write problem.
- **Solution:** Outbox table in the same transaction as the order creation. A background publisher polls or listens via CDC, dispatches to RabbitMQ, and updates lease status with at-least-once semantics.
- **Verification:** 20 specific test cases in `SubmitOrderCompensationFailureTests` and `OutboxCrashWindowTests` test:
  1. Queue rejection after reservation -> automatic compensation and stock refund.
  2. Broker connection loss before ACK -> message retained in Outbox, safe replay.
  3. Worker crash after DB commit -> idempotent consumer detects existing order ID, skips reprocessing without duplicate payment.

---

## 3. Real Empirical Evidence

From `docs/evidence/2026-10-23-50-contenders-10-units.md`:
- **Scenario:** 50 concurrent client threads contesting exactly 10 units.
- **Results:**
  - Accepted Orders: exactly 10 (HTTP 202 -> Confirmed).
  - Rejected Requests: exactly 40 (HTTP 409 Conflict).
  - PostgreSQL Final Stock: exactly 0.
  - Oversold Quantity: **0**.
  - Duplicate Requests with identical `Idempotency-Key`: 100% deduplicated with 0 duplicate orders.

---

## 4. How to Explain in an Interview
1. **Explain the Invariant First:** "Our invariant was absolute: never sell unit 11. Even under broker crash, process crash, or network partition, consistency is preserved."
2. **Explain the Two-Tier Trade-off:** "We didn't rely on Redis as the source of truth. Redis is purely an admission control filter. The ledger and database own the final stock balance."
3. **Walk through the Failure Modes:** "When the queue fails, we catch the exception, release the Redis lease, and return an explicit error. When the worker crashes after DB commit, the transactional outbox ensures the downstream event is eventually dispatched."
