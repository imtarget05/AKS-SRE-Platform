# Interview Diagrams — AKS-SRE Platform

Companion diagrams to ADRs 001–021, for technical interview defense.

## 1. Request Lifecycle

```mermaid
flowchart TD
    subgraph "Client → AKS"
        C1[HTTP Request] -->|TLS + Auth| API-GW[API Gateway]
        API-GW -->|Route & Rate Limit| AKS-API[API Server]
        AKS-API -->|Admission Controllers| Admit[Validating Admission]
        Admit -->|Admitted| Pod[Pod]
        Pod -->|Business Logic| App[LegacyApp / Legacy Service]
        App -->|Response| Pod
        Pod -->|HTTP Response| API-GW
        API-GW -->|Unwrap| C1
    end

    subgraph "Side Effects"
        Pod -->|Structured Logs| Logs[Elasticsearch / Loki]
        Pod -->|Metrics| Prometheus[Prometheus]
        Pod -->|Traces| Jaeger[Jaeger]
    end

    note end note : Request enters via TLS-authenticated API Gateway, passes through
    admission control for policy enforcement, then executes business logic in the
    pod. All side-effects (logs, metrics, traces) are captured asynchronously.

    style Client fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style API-GW fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style AKS-API fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style Pod fill:#ffeb3b,stroke:#fbc02d,stroke-width:2px
    style App fill:#c5e1a5,stroke:#689f38,stroke-width:2px
```

## 2. Transaction Boundary

```mermaid
flowchart TD
    subgraph "Transaction Scope"
        D1[Order Service] -->|Begin Tx| TM[Transaction Manager]
        TM -->|Enlist| D2[Inventory Service]
        D2 -->|Reserve Stock| D3[Stock Cache]
        D3 -->|Confirm Reserve| TM
        TM -->|Enlist| D4[Payment Service]
        D4 -->|Process Payment| D5[Payment Gateway]
        D5 -->|Confirm Payment| TM
        TM -->|Commit| D1
    end

    note end note : Transaction boundary encompasses order service, inventory
    reservation, and payment processing. All participants must either commit or
    roll back atomically. Idempotency keys prevent double-charging on retry.

    style D1 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style TM fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style D2 fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style D3 fill:#ffe0b2,stroke:#fb8c00,stroke-width:2px
    style D4 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style D5 fill:#ffe0b2,stroke:#fb8c00,stroke-width:2px
```

## 3. Message Flow

```mermaid
flowchart TD
    subgraph "Pub/Sub Pattern"
        P1[Order Publisher] -->|Order Event| broker[Redis Stream / Kafka]
        broker -->|Consume| O1[Order Microservice]
        broker -->|Consume| O2[Inventory Microservice]
        broker -->|Consume| O3[Notification Microservice]
    end

    note end note : Order event is published to a durable stream. Multiple
    microservices consume independently. At-least-once delivery requires idempotent
    handlers. Dead-letter queue captures undeliverable messages after max retries.

    style P1 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style broker fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style O1 fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style O2 fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style O3 fill:#fff3e0,stroke:#f57c00,stroke-width:2px
```

## 4. Recovery

```mermaid
flowchart TD
    subgraph "Failure Recovery"
        F1[Failure Detected] -->|Health Check| F2[Circuit Breaker]
        F2 -->|Open| F3[Fallback Route]
        F3 -->|Degrade| F4[Graceful Degradation]
        F4 -->|Restore| F5[Circuit Close]
        F5 -->|Probe| F1
    end

    note end note : Circuit breaker monitors failure rate. After threshold,
    circuit opens and traffic is routed to fallback. After cooldown, circuit
    closes and normal service is probed for restoration.

    style F1 fill:#ffcc80,stroke:#fb8c00,stroke-width:2px
    style F2 fill:#ffcc80,stroke:#fb8c00,stroke-width:2px
    style F3 fill:#fff5e1,stroke:#ffb74d,stroke-width:2px
    style F4 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style F5 fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
