# Curriculum Vitae — Senior Software Engineer (Backend / Distributed Systems)

**Candidate:** Mai Nguyễn Bình Tân  
**Focus:** High-concurrency backend services, distributed systems resilience, transactional integrity, and zero-loss architectures.  
**Core Technologies:** C# / .NET 10, Java 17 / Spring Boot 3, Python 3.11 / FastAPI, PostgreSQL, MySQL, Redis, RabbitMQ, Docker, Kubernetes.

---

## Professional Summary
Senior Software Engineer with deep expertise in designing and engineering resilient, high-concurrency transactional backends. Proven track record tackling extreme race conditions, overselling risks, dual-write consistency hazards, and database contention under flash-sale traffic bursts. Strong advocate of Clean Architecture boundaries, test-driven development (TDD), empirical load testing (k6), and cold disaster recovery verification with explicit data loss boundary analysis.

---

## Demonstrated Technical Achievements (Evidence-Backed)

### 1. Flash-Sale Order Reliability Platform (`services/opsbridge-flashsale`)
*Stack: .NET 10 (C# 13), ASP.NET Core, PostgreSQL 15, Redis 7, RabbitMQ 3, Docker, Kubernetes.*
- **Mitigated Flash-Sale Overselling Under Heavy Contention:** Engineered a two-tier inventory reservation system combining a sub-millisecond Redis fast-fail layer with atomic PostgreSQL row locks (`SELECT ... FOR UPDATE`).
- **Live Cluster Load Testing (k6 on Kubernetes):** Proved zero overselling and strict SLA compliance under empirical concurrency bursts:
  - 50 concurrent buyers competing for 5 limited inventory items (iPhone 15 Pro Max) via Envoy Gateway: exactly 5 accepted (HTTP 202), 45 rejected as sold-out (HTTP 409), 0 server errors (0 5xx), p95 latency **132.2 ms**, stock reduced from 5 to exactly 0 in both PostgreSQL and Redis (`load-tests/k6`).
  - 50 concurrent buyers on abundant stock: 100% accepted with 0 errors, p95 latency **68.36 ms**.
- **Resilient Transactional Outbox Pattern:** Eliminated dual-write failure windows between database transactions and message broker publishing. Built lease-based outbox dispatcher with compensation routines for queue failures, broker crashes, and worker failures, verified by 20 crash-window integration tests.
- **Delivery & CI Verification:** Achieved 100% green remote CI verification on PR #6 ([Run 40067314371](https://github.com/imtarget05/FlashSale-Backend/actions/runs/40067314371)) and main CI ([Run 40067784351](https://github.com/imtarget05/FlashSale-Backend/actions/runs/40067784351)). Testing pyramid comprises 371 automated tests passing locally (`make test-ops`).

### 2. Multi-Outlet Core Banking Ledger (`services/retail-finance`)
*Stack: Java 17, Spring Boot 3, MySQL 8, Flyway, Testcontainers.*
- **Atomic Account & Initial Deposit Lifecycle:** Bound user onboarding, `CASH_IN` journal posting, and regulatory audit creation in a single atomic `@Transactional` boundary, preventing orphan accounts during network interruptions.
- **Tenant Isolation & Security Hardening:** Implemented strict outlet-scoped authorization at the service layer. Verified isolation across cross-outlet balance tampering and request replay attacks (verified by 31 integration tests running on real MySQL 8 Testcontainers, `docs/evidence/retail-outlet-authorization-evidence.md`).
- **Schema Migration (Flyway V2):** Integrated `V2__account_outlet_scope.sql` adding nullable `outlet_id`, index (`idx_account_outlet`), and foreign key constraint (`fk_account_outlet`) to support multi-tenant outlet scoping, verified via `FlywaySchemaValidationIT`.
- **Delivery & CI Verification:** Merged PR #14 on `retail-finance-core-platform` (`433447f`) with 7/7 remote checks green ([Run 40067431737](https://github.com/imtarget05/retail-finance-core-platform/actions/runs/40067431737)) and CodeQL green ([Run 40067645162](https://github.com/imtarget05/retail-finance-core-platform/actions/runs/40067645162)). Local suite: 76/76 PASS (`make test-retail`).

### 3. Warehouse Operations & FEFO Inventory Engine (`services/quanlykho`)
*Stack: Python 3.11, FastAPI, SQLAlchemy 2.x, PostgreSQL 16, Alembic, Pytest.*
- **FEFO (First-Expired, First-Out) Outbound Allocation:** Designed automated lot-selection algorithm prioritizing shortest expiration dates during outbound order fulfillment to prevent product spoilage and inventory discrepancies.
- **Maker-Checker & Keyset Pagination:** Built approval workflow with cryptographic idempotency keys, dual-checker conflict guards, and keyset pagination handling 500+ SKU catalogs without memory bloat.
- **Delivery & CI Verification:** Merged PR #4 on `QuanLyKho` (`b37c92a`) with 7/7 remote checks green ([Run 40070771802](https://github.com/imtarget05/QuanLyKho/actions/runs/40070771802)) and main CI 6/6 jobs green ([Run 40071484737](https://github.com/imtarget05/QuanLyKho/actions/runs/40071484737)). Full suite passes 714 tests on isolated PostgreSQL (`make test-quan`).

---

## Technical Competencies
- **Languages:** C# (.NET 10), Java (17 LTS), Python (3.11), SQL.
- **Frameworks:** ASP.NET Core Web API, Spring Boot 3, FastAPI, SQLAlchemy 2.x, EF Core 10.
- **Databases & Caches:** PostgreSQL (15/16), MySQL (8.0), Redis (7.x).
- **Messaging & Event-Driven:** RabbitMQ, Transactional Outbox, Idempotent Consumers, Dead Letter Queues.
- **Testing & Verification:** xUnit, JUnit 5, Pytest, Testcontainers, k6 concurrency harnesses.
- **Containers & Cloud:** Docker multi-stage builds, non-root containers, Kubernetes manifests, Helm, Kustomize, Envoy Gateway.
