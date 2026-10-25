# Curriculum Vitae — Software Architect / Principal Systems Architect

**Candidate:** Mai Nguyễn Bình Tân  
**Focus:** Enterprise polyglot architectures, domain-driven design, financial ledger invariants, multi-tenant boundaries, and resilient distributed messaging.  
**Core Technologies:** Java 17, C# / .NET 10, Python 3.11, PostgreSQL, MySQL, Redis, RabbitMQ, Clean Architecture, DDD, Event-Driven Architecture, Kubernetes, Envoy Gateway.

---

## Executive Summary
Enterprise Software Architect with extensive experience designing distributed platforms, core banking ledgers, and high-concurrency commerce backends. Specializes in enforcing strict Clean Architecture boundaries, double-entry financial bookkeeping invariants, expand-and-contract schema evolution, and provable tenant isolation. Champion of evidence-based architectural decision records (ADRs), shift-left automated architecture fitness functions, and verifiable disaster recovery automation.

---

## Core Architectural Deliverables & Case Studies

### 1. Enterprise Polyglot Monorepo Architecture
*Target: Unified Engineering Monorepo (`Senior-Engineering-Portfolio`)*
- **Layered Clean Architecture Enforcement:** Standardized Clean Architecture across three distinct enterprise ecosystems (.NET 10, Java 17, Python 3.11). Decoupled pure domain logic from persistence adapters (EF Core, Hibernate, SQLAlchemy) and infrastructure brokers (RabbitMQ, Redis).
- **Architecture Dependency Guarding:** Enforced architectural rules via automated fitness tests (`ArchitectureTests.cs`), failing builds if Domain or Application layers take unauthorized dependencies on frameworks or adapters.
- **Unified North-South Gateway API Routing:** Established platform-level ingress using Envoy Gateway v1.9.1. Routed independent polyglot domains (FlashSale .NET on `flashsale.local`, Legacy Inventory Node.js on `legacy.local`) over a single shared Gateway class without route collisions or cross-namespace permission leaks.

### 2. Double-Entry Core Banking Ledger (`services/retail-finance`)
*Stack: Java 17, Spring Boot 3, MySQL 8, Flyway, Testcontainers.*
- **Immutable Financial Ledger:** Architected double-entry journal system where account balances are strictly derived from immutable debit/credit entries, guaranteeing zero balance discrepancy across synthetic test workloads.
- **Multi-Tenant Boundary Architecture:** Formulated service-layer authorization model enforcing outlet scoping across POS transactions. Verified that outlet credentials cannot read, mutate, or settle cross-outlet accounts even under token replay (`docs/interview-notes/case-study-2-ledger-architecture.md`).
- **Multi-Tenant Schema Evolution (Flyway V2):** Designed `V2__account_outlet_scope.sql` introducing nullable `outlet_id`, index, and foreign key constraint for outlet isolation while safely leaving historical accounts unassigned (NULL) to prevent unauthorized attribution. Verified on real MySQL 8 Testcontainers (`FlywaySchemaValidationIT`).

### 3. High-Concurrency Event-Driven Order Platform (`services/opsbridge-flashsale`)
*Stack: .NET 10, PostgreSQL 15, Redis 7, RabbitMQ 3, Envoy Gateway.*
- **Distributed Consistency Without 2PC:** Replaced distributed two-phase commit (2PC) protocols with a local Transactional Outbox pattern paired with idempotent consumers, ensuring at-least-once delivery with zero duplicate business execution.
- **Admission Control & Graceful Degradation:** Designed two-tier inventory reservation combining sub-millisecond in-memory filtering (Redis Lua) with transactional row-level isolation (PostgreSQL). Proved 0 overselling under extreme flash-sale spikes (50 concurrent buyers on 5 units -> exactly 5 accepted, 45 rejected with HTTP 409, 0 oversold, p95 = 132.2 ms, `load-tests/k6`).
- **Database Disaster Recovery Benchmark (Cold Local Kind Test Harness):** Benchmarked recovery from catastrophic database loss (`DROP DATABASE WITH (FORCE)`) in **0.570 seconds** (RTO measured under cold local Kind test harness, analyzing cold snapshot boundaries and delta transaction loss implications; `docs/evidence/real-workload-dr-drill-PASS.md`).

---

## Architectural Principles & Skills
- **Architectural Paradigms:** Clean Architecture, Hexagonal / Ports & Adapters, Domain-Driven Design (DDD), Event-Driven Architecture (EDA), CQRS.
- **Data Architecture:** Double-Entry Bookkeeping, Transactional Outbox Pattern, Read-Write Separation, Schema Expand-and-Contract.
- **Resilience & Reliability:** Circuit Breakers, Retry with Exponential Backoff & Jitter, Dead-Letter Queues, Compensating Transactions.
- **Security & Multi-Tenancy:** Defense-in-depth, RBAC & Attribute-Based Access Control, JWT Security Lifecycles, PII Protection.
