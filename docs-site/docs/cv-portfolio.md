# CV Portfolio — For Recruiters

> **Senior Software Engineer | Cloud Platform Engineer | DevSecOps**
>
> Contact: tanmainguyenbinh@gmail.com | GitHub: [imtarget05](https://github.com/imtarget05)

---

## 🚀 Live Demo Projects

### 1. Enterprise RAG Document Intelligence Platform
**Demo:** [smart-doc-chatbot.pages.dev](https://smart-doc-chatbot.pages.dev)

**What it does:** Upload any PDF/document → AI answers questions using Corrective RAG with self-evaluation

**Tech:** Spring Boot 3 · React (Vite) · LangChain Python Agent · Qdrant (vector DB) · Kafka · Redis · Azure Container Apps · Cloudflare Pages

**Key achievements:**
- Corrective RAG with LangGraph agent that self-evaluates retrieval quality
- Kafka event-driven cache invalidation reducing repeated search latency 80%
- 55/55 unit tests + 23/23 Kafka integration tests — all pass in CI

---

### 2. FlashSale Microservices + OpsBridge Observability
**Demo:** [opsbridge-dashboard.pages.dev](https://opsbridge-dashboard.pages.dev)

**What it does:** Flash sale platform handling 50 concurrent buyers with zero inventory oversell

**Tech:** .NET 10 · CQRS/EventSourcing · PostgreSQL · Redis · RabbitMQ · Azure AKS · GitOps/ArgoCD

**Key achievements:**
- Concurrency-safe inventory: 50 simultaneous buyers, stock=10 → exactly 10 orders, 0 oversell
- 172/172 unit tests PASS, 0 HIGH/CRITICAL Trivy findings
- OpsBridge observability dashboard with real-time metrics via SignalR

---

### 3. Quản Lý Kho Trà Sữa (Inventory Management)
**Demo:** [quan-ly-kho-tra-sua.tanmainguyenbinh.workers.dev](https://quan-ly-kho-tra-sua.tanmainguyenbinh.workers.dev)

**What it does:** Real-time inventory tracking for bubble tea shop with AI forecasting

**Tech:** Flutter 3.47 Web · FastAPI · PostgreSQL · MLflow · Cloudflare Workers (BFF proxy) · Google OAuth 2.0

**Key achievements:**
- 191/191 Flutter tests PASS
- AI inventory forecasting with MLflow experiment tracking
- Cloudflare Worker as edge BFF proxy (zero server-side latency overhead)

---

### 4. AKS SRE Platform Blueprint
**Evidence Site:** [aks-sre-platform.pages.dev](https://aks-sre-platform.pages.dev) (this site)

**What it does:** Production-grade Kubernetes platform on Azure with GitOps, SRE gates, and Zero-Trust identity

**Tech:** Terraform · Azure AKS (v1.36) · ArgoCD · Prometheus · Grafana · Workload Identity Federation

**Key achievements:**
- 47/47 SRE gate tests PASS, 16/0 GitOps validation
- Zero static secrets: Workload Identity Federation for all Azure resource access
- Private ACR image pull by digest (imagePullSecrets: []) — verified on real AKS

---

## Technical Profile

| Domain | Technologies |
|--------|-------------|
| **Languages** | Java (Spring Boot) · Python (FastAPI, LangChain) · Dart (Flutter) · C# (.NET 10) · TypeScript |
| **Cloud** | Azure (AKS, Container Apps, ACR, PostgreSQL Flexible, Redis, Event Hubs) |
| **Edge** | Cloudflare Pages · Workers · Worker Assets |
| **DevOps** | GitHub Actions · ArgoCD GitOps · Terraform · Docker · Kubernetes |
| **Data** | PostgreSQL · Redis · Qdrant (vector) · Kafka · RabbitMQ · MLflow |
| **Observability** | Prometheus · Grafana · OpenTelemetry · Azure Monitor |
| **Security** | Trivy · Workload Identity · RBAC · Network Policies |
