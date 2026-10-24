# Unified 5-Repository Architecture & Ecosystem Flow

> **Scope**: Cross-Repository Systems Integration (`OpsBridge`, `QuanLyKho`, `retail-finance-core-platform`, `AKS-SRE-Platform`, `SmartDocumentChatbot`)  
> **Key References**: [Master Architecture Guide](https://github.com/imtarget05/OpsBridge/blob/main/docs/architecture/UNIFIED_CROSS_REPO_ARCHITECTURE.md) · [Portfolio Audit](https://github.com/imtarget05/AKS-SRE-Platform/blob/main/docs/evidence/portfolio-audit-2026-10-21.md)

---

## 1. Executive Platform Architecture

The portfolio consists of five decoupled systems operating across high-throughput commerce, physical warehouse logistics, double-entry financial accounting, conversational AI intelligence, and cloud-native infrastructure automation.

=== "Ecosystem Overview"
    ```mermaid
    flowchart TD
        subgraph Ingress ["API Gateway & Ingress"]
            GW[TLS / Rate-Limited Ingress Controller]
        end

        subgraph TierCommerce ["Commerce & Order Tier"]
            OB["OpsBridge (.NET 10 / C# 13)<br/>• Flash-Sale Admission<br/>• Redis Lua CAS Fast-Fail<br/>• Outbox Event Publisher"]
        end

        subgraph TierLogistics ["Logistics & Warehousing"]
            QLK["QuanLyKho (Python 3.11 / FastAPI)<br/>• Maker-Checker Dual Control<br/>• FEFO Lot Expiration<br/>• Signed Webhooks"]
        end

        subgraph TierFinance ["Financial Ledger Tier"]
            RF["retail-finance-core (Java 17 / Spring Boot 3)<br/>• Double-Entry Bookkeeping<br/>• Optimistic Lock (@Version)<br/>• Daily Python Recon Engine"]
        end

        subgraph TierAI ["AI & Document Intelligence"]
            SD["SmartDocumentChatbot (Next.js / FastAPI)<br/>• Corrective RAG (CRAG)<br/>• Multi-Tenant PGVector Retrieval<br/>• Langfuse Tracing & Circuit Breaker"]
        end

        subgraph SREPlatform ["Cloud-Native SRE Platform"]
            AKS["AKS-SRE-Platform (K8s / GitOps / Calico)<br/>• Zero-Trust Network Isolation<br/>• PDB Zero-Downtime Drains<br/>• Prometheus & Automated SRE Runbooks"]
        end

        GW -->|/api/orders| OB
        GW -->|/inventory| QLK
        GW -->|/api/v1/ledger| RF
        GW -->|/chat| SD

        QLK -->|HMAC Webhook: GoodsReceipt| OB
        OB -->|Outbox Event: OrderFulfilled| RF
        SD -->|Audit Queries & Traces| RF

        AKS -.->|Orchestrates, Isolates & Monitors| OB
        AKS -.->|Orchestrates, Isolates & Monitors| QLK
        AKS -.->|Orchestrates, Isolates & Monitors| RF
        AKS -.->|Orchestrates, Isolates & Monitors| SD
    ```

=== "Invariant Matrix"
    | System | Core Invariant | Guard Mechanism | Verification Gate |
    |---|---|---|---|
    | **OpsBridge** | **Zero Overselling** | Redis Lua CAS admission + Postgres conditional SQL (`Stock >= @qty`) | Concurrency harness: 50 buyers / 10 stock $\rightarrow$ 10 fills, 40 fast-fails |
    | **retail-finance** | **Ledger Parity** | Double-Entry balance ($\sum \text{Debits} = \sum \text{Credits}$) + JPA `@Version` | Testcontainers MySQL integration suite |
    | **QuanLyKho** | **Two-Man Rule** | Maker-Checker separation (`maker_id != checker_id`) + FEFO lots | Pytest maker-checker authorization tests |
    | **AKS-SRE** | **Zero-Downtime Resilience** | Calico zero-trust NetworkPolicies + PDB drain tolerance | Gate harness `tests/test_gates.py` (47 pass) |
    | **SmartDoc** | **Tenant Data Isolation** | Owner-filtered vector queries + Resilience4j circuit breaker | ADR-0001 tenant retrieval validation |

---

## 2. Cross-Repository Lifecycles & Integration Flows

### Scenario 1: Flash Sale Order to General Ledger Settlement

```mermaid
sequenceDiagram
    autonumber
    actor C as "Customer"
    participant API as "OpsBridge: Order.Api"
    participant Redis as "Redis Cache (CAS)"
    participant Broker as "RabbitMQ Topic Exchange"
    participant Worker as "OpsBridge: Order.Worker"
    participant DB as "OpsBridge: PostgreSQL"
    participant Finance as "retail-finance: Spring Boot Core"
    participant GL as "retail-finance: MySQL 8 (GL)"

    C->>API: POST /api/orders (IdempotencyKey, ProductId, Qty)
    API->>Redis: Atomic Lua CAS (stock >= qty)
    alt Out of Stock
        Redis-->>API: 0 (Sold out)
        API-->>C: 409 Conflict
    else Reserved
        Redis-->>API: 1 (Reserved)
        API->>Broker: Enqueue OrderPlacementTask
        API-->>C: 202 Accepted (processing)
    end

    Note over Worker,DB: Async Fulfillment & Outbox Insertion
    Worker->>Broker: Dequeue Task
    Worker->>DB: BEGIN TRANSACTION
    Worker->>DB: UPDATE Products SET Stock = Stock - @qty WHERE Stock >= @qty
    Worker->>DB: INSERT INTO Orders (Fulfilled)
    Worker->>DB: INSERT INTO OutboxMessages ('OrderFulfilled.v1')
    Worker->>DB: COMMIT TRANSACTION

    Note over Worker,Finance: Transactional Outbox Relay
    Worker->>Broker: Publish 'OrderFulfilled.v1' (Publisher Confirms)
    Broker->>Finance: Deliver 'OrderFulfilled.v1'
    Finance->>GL: Deduplicate via Unique Index
    Finance->>GL: BEGIN TRANSACTION
    Finance->>GL: Check Account @Version & Balance Parity
    Finance->>GL: INSERT INTO JournalEntries (Debit Cash, Credit Revenue)
    Finance->>GL: UPDATE Accounts SET Balance, Version = Version + 1
    Finance->>GL: COMMIT TRANSACTION
```

> [!NOTE]
> **No Distributed 2-Phase Commit (2PC)**:
> The system eliminates the distributed dual-write hazard by enclosing order state mutation and the outbox event record within a single local ACID transaction. The downstream financial system relies on idempotent deduplication (`uk_txn_idempotency`) and optimistic locking.

---

### Scenario 2: Warehouse Goods Receipt & 3-Way Reconciliation

```mermaid
sequenceDiagram
    autonumber
    actor Maker as "Warehouse Worker (Maker)"
    actor Checker as "Warehouse Manager (Checker)"
    participant QLK as "QuanLyKho API"
    participant OpsRecon as "OpsBridge: 3-Way Engine"
    actor Auditor as "Auditor"

    Maker->>QLK: Draft Goods Receipt Voucher (Lot, Expiry Date)
    Checker->>QLK: Approve Voucher
    Note over QLK: Server verifies checker_id != maker_id
    QLK->>QLK: Commit Stock Increase (FEFO Order) & Outbox Event
    QLK->>OpsRecon: Signed Webhook (HMAC-SHA256)
    OpsRecon->>OpsRecon: Match (Purchase Order, Goods Receipt, Supplier Invoice)
    alt Quantities & Prices within ±1% Tolerance
        OpsRecon-->>OpsRecon: Status = AUTO_MATCHED
    else Variance Detected (Price drift / Missing SKU)
        OpsRecon-->>Auditor: Flag Discrepancy & Create Review Ticket
    end
```

---

## 3. C4 Level 2: Container Ecosystem

```mermaid
flowchart TD
    subgraph IngressLayer ["Ingress & Security Perimeter"]
        Ingress["Envoy / NGINX Ingress Controller<br/>(TLS Termination & Rate Limiting)"]
    end

    subgraph K8sNamespaceOps ["Namespace: opsbridge"]
        O_API["Order.Api (.NET 10)"]
        O_Worker["Order.Worker (.NET 10)"]
        O_Redis[("Redis Lua Cache")]
        O_DB[("PostgreSQL 16")]
        O_Broker["RabbitMQ 3.13 Broker"]
    end

    subgraph K8sNamespaceQLK ["Namespace: quanlykho"]
        Q_API["QuanLyKho Web API (FastAPI)"]
        Q_DB[("PostgreSQL 16")]
        Q_Worker["ETL Background Worker"]
    end

    subgraph K8sNamespaceFinance ["Namespace: finance"]
        F_Core["Core Ledger Service (Spring Boot 3)"]
        F_DB[("MySQL 8 General Ledger")]
        F_Recon["Python Recon Service"]
    end

    subgraph K8sNamespaceAI ["Namespace: smartdoc"]
        A_UI["Next.js 14 Frontend"]
        A_Engine["FastAPI CRAG Engine"]
        A_VecDB[("PGVector Database")]
        A_Langfuse["Langfuse Server"]
    end

    subgraph K8sNamespacePlatform ["Namespace: monitoring & argocd"]
        S_Prom["Prometheus Metrics Collector"]
        S_Argo["Argo CD Controller"]
    end

    Ingress -->|/api/orders| O_API
    Ingress -->|/inventory| Q_API
    Ingress -->|/api/v1/ledger| F_Core
    Ingress -->|/chat| A_UI

    O_API --> O_Redis
    O_API --> O_Broker
    O_Worker --> O_Broker
    O_Worker --> O_DB

    Q_API --> Q_DB
    Q_Worker --> Q_DB
    Q_API -.->|HMAC Webhook| O_API

    O_Worker -.->|RabbitMQ Event| F_Core
    F_Core --> F_DB
    F_Recon --> F_DB

    A_UI --> A_Engine
    A_Engine --> A_VecDB
    A_Engine --> A_Langfuse

    S_Prom -.->|Scrape /metrics| O_API
    S_Prom -.->|Scrape /metrics| Q_API
    S_Prom -.->|Scrape /actuator| F_Core
    S_Prom -.->|Scrape /metrics| A_Engine
    S_Argo -.->|Reconcile State| K8sNamespaceOps
    S_Argo -.->|Reconcile State| K8sNamespaceQLK
    S_Argo -.->|Reconcile State| K8sNamespaceFinance
    S_Argo -.->|Reconcile State| K8sNamespaceAI
```

---

## 4. Kubernetes Zero-Trust Network & Infrastructure Fabric

Workloads run in isolated namespaces governed by Calico NetworkPolicies. Default-deny policies prevent unauthenticated lateral movement.

### Calico Policy Enforcement Matrix

| Source | Destination | Protocol/Port | Action | Security Rationale |
|---|---|---|---|---|
| `ingress-nginx` | Workload APIs | HTTP (8080/8000/3000) | **ALLOW** | Public client ingress through WAF |
| `quanlykho` | `opsbridge/order-api` | HTTP (8080) | **ALLOW** | Authorized HMAC GoodsReceipt webhook |
| `finance` | `opsbridge/rabbitmq` | AMQP (5672) | **ALLOW** | Async consumption of order events |
| `smartdoc` | `finance/mysql` | MySQL (3306) | **DENY** | Zero direct cross-database access |
| `opsbridge` | `finance/core` | ANY | **DENY** | Enforces asynchronous event-driven boundary |
| Any Workload | External Internet | ANY | **DENY** | Egress lockdown (except whitelisted APIs) |

> [!IMPORTANT]
> **PDB Zero-Downtime Guarantee**:
> Every critical application deployment specifies a `PodDisruptionBudget`. During Kubernetes node drains or maintenance windows, the cluster scheduler guarantees at least one replica remains ready to serve traffic without dropping in-flight HTTP connections.

---

## 5. AI Corrective RAG (CRAG) & Advisory Governance

### SmartDocumentChatbot CRAG Routing Hierarchy
1. **Owner-Filtered Retrieval**: Vector search explicitly filters on `owner_username = @current_user` in PGVector, guaranteeing tenant isolation.
2. **Relevance Grading**: A cross-encoder grades retrieved chunks between $0.0$ and $1.0$.
3. **Circuit Breaker Fallback**: If retrieval confidence falls below $0.4$ or times out, a Resilience4j circuit breaker trips to a safe, deterministic keyword search or human escalation prompt.
4. **Langfuse Distributed Tracing**: Every step logs execution traces (`trace_id`, token counts, latencies, retrieval confidence).

### QuanLyKho Advisory Boundary (ADR-0002)
- AI risk scores in warehouse inventory are strictly **advisory**.
- Autonomous state mutations by AI agents are prohibited.
- Model inferences are stamped with a **SHA-256 model provenance checksum**.
