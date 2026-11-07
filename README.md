# AKS-SRE-Platform — Production-Ready Azure Kubernetes Platform Blueprint & SRE Operations

[![Platform Tests](https://img.shields.io/badge/Gate%20Suite-62%20Assertions%20(G1--G16)-blue?style=flat-square)](tests/test_gates.py)
[![SRE Incident Agent](https://img.shields.io/badge/SRE%20Incident%20Agent-86.74%25%20Coverage-success?style=flat-square)](app/sre_incident_agent/)
[![Microservice Tests](https://img.shields.io/badge/API%20Tests-12%2F12%20Passed-brightgreen?style=flat-square)](app/sre-demo-api/)
[![GitOps Engine](https://img.shields.io/badge/Argo%20CD-v3.5.5%20(Zero%20Wildcards)-orange?style=flat-square)](platform/argocd/VERSION)
[![Policy Gate](https://img.shields.io/badge/Policy%20Gate-121%20Objects%20Passed-teal?style=flat-square)](scripts/policy-gate.py)
[![Terraform IaC](https://img.shields.io/badge/Terraform%20IaC-AzureRM%20~%3E%205.0%20(5%20Modules)-623CE4?style=flat-square)](terraform/)

> **A production-engineered Azure Kubernetes Service (AKS) platform blueprint demonstrating cloud-native infrastructure, automated GitOps delivery, multi-layer admission policy gates, high-resilience backend API patterns, and an automated read-only SRE incident response agent.**

---

## 1. Quick Overview & Recruiter Highlights (60–90 Second Scan)

- **Target Engineering Roles:** Senior Backend Software Engineer, Platform / DevOps Engineer, Site Reliability Engineer (SRE).
- **Core Engineering Philosophy:** Reliability is an architectural property, not an operational afterthought. Concurrency control, failure containment, zero-trust network boundaries, and deterministic policy gates must be enforced in code, verified by automated test suites, and audited before cloud deployment.
- **What Was Built:**
  - **Modular Cloud Infrastructure:** 5 decoupled Terraform modules (AKS cluster, networking, ACR identity attachment, and observability) running on AzureRM provider `~> 5.0` with Azure AD-authenticated remote state and OIDC Workload Identity.
  - **Zero-Trust GitOps Pipeline:** Declarative continuous delivery via Argo CD `v3.5.5` using server-side apply and strictly bounded `AppProject` RBAC with **zero wildcard permissions (`*`)**.
  - **Multi-Layer Static Policy Gates:** Automated admission gate (`scripts/policy-gate.py`) scanning 121 objects across 6 Kustomize roots to enforce Kubernetes Pod Security Standards, immutable digest/tag pinning, and mandatory resource envelopes.
  - **Resilient Backend Workload (`sre-demo-api`):** Production-grade Node.js 22 microservice implementing **decoupled health probes** (`/health/live` vs `/health/ready`) to prevent cascading restart loops, Prometheus RED metrics, and OpenTelemetry distributed tracing.
  - **Automated SRE Incident Agent:** Python-based read-only incident response workflow (`app/sre_incident_agent/`) orchestrating alert triage, diagnostics, and incident briefing with **86.74% automated test coverage**.
  - **Edge Security Contract:** Cloudflare Worker edge router (`platform/cloudflare/api-edge`) validating mTLS origin binding against Azure Envoy Gateway and sanitizing spoofable caller identity headers.

### Key Metrics & Verifiable Facts

| Dimension | Measured Metric | Verification Command & Source |
| :--- | :--- | :--- |
| **Policy Enforcement** | **121 objects passed** across 6 Kustomize roots | `python3 scripts/policy-gate.py` (`scripts/policy-gate.py:70-160`) |
| **GitOps Integrity** | **38 passed checks**, zero wildcard permissions | `python3 gitops/validate-gitops.py` (`platform/argocd/appproject.yaml`) |
| **Gate Regression** | **62 assertions** across G1–G16 test matrix | `.venv/bin/python tests/test_gates.py` (`tests/test_gates.py`) |
| **SRE Agent Coverage** | **86.74% statement coverage** (52 unit tests) | `.venv/bin/python -m pytest tests/` (`app/sre_incident_agent/`) |
| **Microservice Suite** | **12/12 unit tests passing** (0 failures) | `npm --prefix app/sre-demo-api test` (`app/sre-demo-api/`) |
| **Edge Router Contract**| **7/7 unit tests passing** (0 failures) | `node --test platform/cloudflare/api-edge/test/*.test.mjs` |
| **Terraform Validity** | **5/5 modules validated** (AzureRM v5) | `terraform -chdir=terraform/<module> validate` |
| **Legacy Tech Parity** | **0 .NET files** (`.cs`, `.csproj`, `.sln`) | Repository root static search (Clean stack) |

### Live Interactive Mirrors & Infrastructure Boundaries

To demonstrate the runtime behavior without incurring continuous cloud hosting costs, public demo interfaces are mirrored on managed services:
- **Live SRE Management Console:** [https://aks-sre-platform.pages.dev/](https://aks-sre-platform.pages.dev/) (Hosted on Cloudflare Pages)
- **Live Workload Health Probe:** [https://sre-demo-api.onrender.com/health/live](https://sre-demo-api.onrender.com/health/live) (Render preview mirror)

> **Operational Boundary Note:** The Render and Cloudflare Pages endpoints serve as publicly accessible UI/API mirrors for demonstration. They do **not** provide private Azure VNet peering or customer-owned network boundaries. The complete enterprise-grade cloud topology (Azure VNet, Envoy Gateway mTLS, and AKS node pools) is defined in Terraform and verified locally against a 3-node `kind` cluster (Kubernetes v1.36.1) to avoid idle cloud spend ($13/day under subscription quotas). See [Section 7: Operational Honesty](#7-operational-honesty-cloud-state--resource-governance) for details.

---

## 2. End-to-End System Architecture & Ingress Flow

```
                           INTERNET / CLIENT TRAFFIC
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │       Cloudflare Edge Worker (api-edge)          │
             │  - Fixed prefix routing (/flashsale, /quanlykho) │
             │  - Strip caller X-Forwarded-* headers            │
             │  - Edge rate limiting & client cert injection    │
             └────────────────────────┬─────────────────────────┘
                                      │ Mutual TLS (mTLS)
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │            Azure Envoy Gateway Ingress           │
             │  - ClientTrafficPolicy: trusts Cloudflare CA     │
             │  - Gateway API HTTPRoute namespace isolation     │
             │  - Static public IP & managed TLS termination    │
             └────────────────────────┬─────────────────────────┘
                                      │ In-Cluster Overlay Network
       ┌──────────────────────────────┴──────────────────────────────┐
       │                                                             │
       ▼                                                             ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│     AKS System Node Pool     │              │     AKS User Node Pool       │
│  (2x Standard_D4s_v6 Nodes)  │              │  (Autoscaling: 2 to 10 Pods) │
│  - CoreDNS, Metrics Server   │              │                              │
│  - Argo CD v3.5.5 Controller │              │  ┌────────────────────────┐  │
│  - OpenTelemetry Collector   │              │  │  sre-demo-api Workload │  │
│  - Prometheus & Alertmanager │              │  │  - Event Loop /live    │  │
│                              │              │  │  - Dependency /ready   │  │
│                              │              │  │  - RED Metrics /metrics│  │
│                              │              │  └────────────────────────┘  │
└──────────────────────────────┘              └──────────────────────────────┘
```

### 2.1 Request Life Cycle & Ingress Security
1. **Edge Ingestion:** Inbound requests arrive at the Cloudflare Edge Worker (`platform/cloudflare/api-edge`). The Worker enforces route allowlists, terminates client connections, injects an immutable request nonce, and **strips caller-supplied identity headers** (`X-Forwarded-For`, `X-Forwarded-Host`, `X-Forwarded-Proto`) to prevent upstream header spoofing.
2. **mTLS Origin Binding:** Traffic traverses the public internet to Azure using mutual TLS (mTLS). Azure Envoy Gateway applies a `ClientTrafficPolicy` configured with the Cloudflare Client CA. Requests originating from any other source are rejected at the TLS handshake before reaching application compute.
3. **Gateway Routing:** Azure Envoy Gateway processes Kubernetes `HTTPRoute` resources, stripping the path prefix and routing traffic to the internal ClusterIP service belonging to the target tenant namespace (`quanlykho`, `flashsale`, or `portfolio`).
4. **Node Pool Separation:** AKS runs a strictly separated two-tier pool architecture:
   - **System Pool:** Dedicated 2x `Standard_D4s_v6` nodes running critical cluster infrastructure (CoreDNS, Argo CD, Gateway controller, Prometheus). Workloads are tainted against scheduling general application pods here.
   - **User Pool:** Dedicated worker nodes hosting application containers with Horizontal Pod Autoscaling (HPA) and topology spread constraints across Azure Availability Zones.

---

## 3. High-Reliability Backend & SRE Architecture

### 3.1 Decoupled Health Probes Pattern: Preventing Cascading Outages

A common anti-pattern in containerized microservices is coupling liveness probes to backend dependencies (e.g., database pings or downstream API checks). In distributed systems, this creates **cascading restart loops**:

```
Transient DB Latency / Saturation
       │
       ▼
Database queries slow down across all pods
       │
       ▼
Liveness probe timeouts triggered (> 1000ms)
       │
       ▼
Kubelet marks pods unhealthy and KILLS the containers
       │
       ▼
All pods reboot simultaneously → Boot storm overwhelms DB connection pool
       │
       ▼
TOTAL SYSTEM OUTAGE (Cascading Failure)
```

#### The Solution (`app/sre-demo-api/src/server.js:9-22`)
The Node.js workload decouples probe concerns into two distinct architectural endpoints:

```javascript
// 1. LIVENESS PROBE: Answers "Is the process event-loop responsive?" ONLY.
// Never consults downstream databases or dependencies.
if (route === '/health/live' || route === '/health') {
  reply(res, 200, { status: 'live', uptime_s: (Date.now() - startedAt) / 1000 }, route, method);
  return done(200);
}

// 2. READINESS PROBE: Answers "Can this pod safely process customer traffic?"
// Consults downstream dependencies (state.dependencyReady()).
if (route === '/health/ready') {
  const ready = await state.dependencyReady();
  metrics.readiness.set(Number(ready));
  reply(res, ready ? 200 : 503, { status: ready ? 'ready' : 'not-ready', dependency: ready }, route, method);
  return done(ready ? 200 : 503);
}
```

- **Liveness (`/health/live`):** Evaluates whether the Node.js event loop is executing ticks. If a downstream database degrades, liveness remains `HTTP 200`. The container stays alive, retains memory state, and does not restart.
- **Readiness (`/health/ready`):** Evaluates dependency health. If the database degrades, this probe returns `HTTP 503`. The Kubernetes Endpoints controller immediately drops the pod from the Service load balancer. In-flight requests drain gracefully, and new traffic is diverted to healthy replicas without terminating processes.

### 3.2 Defensive Backend API Engineering
- **Host-Header Injection Prevention (`server.js:36-43`):** URLs are parsed against a synthetic authority (`https://workload.invalid`). The incoming `Host` header is ignored during routing decisions, eliminating DNS rebinding and host cache poisoning vectors.
- **Constant-Time Security Comparison (`server.js:114-142`):** Administrative readiness overrides (`/internal/readiness`) require a bearer token validated using `crypto.timingSafeEqual` over SHA-256 digests. This prevents side-channel timing attacks that leak secret tokens byte-by-byte. If `INTERNAL_READINESS_TOKEN` is unset, the endpoint fails closed with `401 Unauthorized`.
- **Deterministic Workload Execution (`/api/work`):** Implements bounded mathematical iterations (capped at 200,000 iterations) measuring exact microsecond user CPU consumption via `process.cpuUsage()`, providing reproducible load for HPA tuning.
- **Fail-Closed Chaos Injection (`/api/fail`):** Test-only failure route disabled in production; returns `404 Not Found` unless explicitly armed via environment configuration.
- **Graceful Lifecycle Draining:** Listens for `SIGTERM`, unregisters readiness, drains active HTTP connections, and enforces a strict 10-second termination deadline.

### 3.3 Observability & Telemetry Pipeline
- **Prometheus RED Metrics:** Custom metrics registry via `prom-client` collecting:
  - `http_requests_total` (Rate): Labeled by route, HTTP method, and status code.
  - `http_errors_total` (Errors): Monitored for 5xx server-side anomalies.
  - `http_request_duration_seconds` (Duration): High-resolution histogram for p50, p95, and p99 latency evaluation.
  - `http_requests_in_flight`: Concurrency gauge tracking active requests.
- **Distributed Tracing:** Auto-instrumented via OpenTelemetry SDK (`@opentelemetry/sdk-node` 0.57.2) exporting via OTLP/HTTP to the platform collector, propagating W3C trace context across outbound HTTP calls.
- **Correlation ID:** Automatically injects a UUIDv4 `x-request-id` header into every request and response, logging structured JSON with trace correlation.

### 3.4 Automated SRE Incident Agent (`app/sre_incident_agent`)
To eliminate human latency during production incidents, the platform embeds an automated, read-only incident triage and diagnostics agent.

```
                  ┌───────────────────────────────┐
                  │    Alertmanager Alert Fired   │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
      ┌───────────────────────────────────────────────────────┐
      │  Stage 1: Alert Triage (TriageVerdict)                │
      │  - Deduplicate & correlate alerts                     │
      │  - Evaluate severity, firing duration, and labels     │
      └───────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
      ┌───────────────────────────────────────────────────────┐
      │  Stage 2: Diagnostics (DiagnosisResult)               │
      │  - PrometheusAdapter: Query rate, error, latency SLIs │
      │  - KubectlAdapter: Inspect pod status, events, logs   │
      │  - ArgoAdapter: Check GitOps sync status & diffs      │
      └───────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
      ┌───────────────────────────────────────────────────────┐
      │  Stage 3: Incident Critic & Brief (IncidentBrief)     │
      │  - Synthesize root cause hypotheses                   │
      │  - Match runbooks (RunbookAdapter)                    │
      │  - Output actionable remediation brief                │
      └───────────────────────────────────────────────────────┘
```

- **Fail-Safe Design:** Strictly read-only adapters (`AlertmanagerAdapter`, `PrometheusAdapter`, `KubectlAdapter`, `ArgoAdapter`, `RunbookAdapter`). The agent has **zero write permissions** (no `kubectl apply/delete`, no Argo CD mutation, no secret access).
- **Deterministic Execution:** Operates completely offline without external network or LLM dependencies for core evaluation.
- **Test Coverage:** Verified by 52 automated tests in pytest achieving **86.74% statement coverage** (exceeding the 75% baseline requirement in `pyproject.toml`).

---

## 4. Platform Engineering & Supply-Chain Security

### 4.1 Modular Infrastructure as Code (Terraform)
The infrastructure is decomposed into 5 reusable, independently verifiable modules (`terraform/aks-foundation`):
- `modules/aks_cluster`: Manages AKS cluster lifecycle, system node pool (2x `Standard_D4s_v6`), user workload node pool, availability zone distribution, and autoscaling quota constraints.
- `modules/networking`: Provisions Azure Virtual Network, private subnets (apps, monitoring, private endpoints), Private DNS zones, and default-deny Network Security Groups (NSGs).
- `modules/acr_attachment`: Grants decoupled `AcrPull` permissions to the AKS kubelet managed identity without hardcoding credentials.
- `modules/observability`: Deploys Azure Monitor Log Analytics workspace, Data Collection Rules (DCR), and OpenTelemetry collector integration.

**IaC Quality Controls:**
- **Provider Pinning:** AzureRM provider constrained to `~> 5.0` with Terraform `>= 1.5`.
- **Identity & State:** Authenticated via Azure OIDC Workload Identity; remote state stored in Azure Blob Storage (`stakssre` container `tfstate`) using Azure AD authentication (`use_azuread_auth = true`).
- **Static & Unit Testing:** All 5 modules pass `terraform validate` and 15 native `terraform test` assertions verifying boundary isolation, autoscaler limits, and role assignments.

### 4.2 Zero-Trust GitOps Delivery (Argo CD)
- **Pinned Version:** Argo CD `v3.5.5` is pinned in a single canonical file (`platform/argocd/VERSION`) to eliminate drift across CI/CD scripts and manifests.
- **Server-Side Apply:** Bootstrapped via Kubernetes server-side apply (`kubectl apply --server-side`) to prevent race conditions with large CustomResourceDefinitions (CRDs).
- **Strict AppProject RBAC (`platform/argocd/appproject.yaml`):**
  - **Zero Wildcard Repositories:** Source repositories are strictly whitelisted to explicit git URLs (`CreditFlow`, `AKS-SRE-Platform`, `QuanLyKho`). Wildcards (`*`) are prohibited.
  - **Zero Wildcard Destinations:** Target namespaces are locked to `quanlykho`, `portfolio`, and `flashsale` on the in-cluster API server.
  - **Cluster-Resource Boundary:** Only `Namespace` resources may be created cluster-wide; all other cluster-scoped mutations (ClusterRole, CRDs) are blocked by the admission controller.
- **Negative Controls:** The validation engine (`gitops/validate-gitops.py`) detects missing external checkouts and emits `EXTERNAL_REPO_NOT_PRESENT`, refusing to report false greens.

### 4.3 Multi-Layer Static Policy Gates (`scripts/policy-gate.py`)
Before any manifest merges into `main` or deploys to a cluster, `scripts/policy-gate.py` renders all 6 maintained Kustomize roots (`deploy/base`, `deploy/base/observability`, `deploy/overlays/*`) and executes 121 compliance checks:
1. **Workload Security:** Enforces `runAsNonRoot: true` and `seccompProfile.type: RuntimeDefault` on all Pod specs.
2. **Container Hardening:** Enforces `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, and Linux `capabilities.drop: ["ALL"]`.
3. **Resource Discipline:** Mandatory `resources.requests` and `resources.limits` for both CPU and Memory on every container to prevent noisy-neighbor starvation.
4. **Image Tag Discipline:** Rejects `:latest` tags, unpinned floating tags, and placeholder registries. Production overlays require 64-character SHA-256 immutable digests.
5. **High Availability:** Requires explicit `topologySpreadConstraints` across failure zones and independent `livenessProbe`, `readinessProbe`, and `startupProbe` definitions on all primary workloads.

### 4.4 Autoscaling & High-Availability Contracts
- **Horizontal Pod Autoscaling (`deploy/base/autoscaling.yaml`):**
  - Minimum Replicas: 2 (ensures redundancy).
  - Maximum Replicas: 10 (bounded capacity protection).
  - Target Utilization: 70% CPU.
  - **Scale-Up Policy:** Reacts within 30 seconds (`stabilizationWindowSeconds: 30`) scaling up to 100% or 4 pods per period.
  - **Scale-Down Policy:** Conservative 5-minute stabilization window (`stabilizationWindowSeconds: 300`) scaling down at most 25% per minute to eliminate pod flapping / thrashing.
- **Pod Disruption Budget (PDB):** Enforces `minAvailable: 1`, allowing rolling cluster upgrades and node drains without service disruption while avoiding drain deadlocks.

---

## 5. Verifiable Claims-to-Evidence Matrix

Every technical claim in this documentation is backed by concrete code, configuration, or test results in this repository:

| Architectural Claim | Implementation Artifact | Line Reference | Verification Command & Result |
| :--- | :--- | :--- | :--- |
| **AzureRM v5 & OIDC Auth** | `terraform/aks-foundation/versions.tf` | Lines 1–19 | `terraform -chdir=terraform/aks-foundation validate` → **Success! Valid.** |
| **Remote Azure AD Backend** | `terraform/aks-foundation/backend-remote.tfbackend.example` | Lines 11–15 | Inspected configuration (`stakssre`, `use_azuread_auth=true`) |
| **5 Modular IaC Roots** | `terraform/aks-foundation/main.tf`, `terraform/modules/*` | Lines 5–54 | `for d in terraform/modules/*; do terraform -chdir=$d validate; done` → **All Valid** |
| **Argo CD Pinned Single-File** | `platform/argocd/VERSION` | Line 1 | `cat platform/argocd/VERSION` → `v3.5.5` |
| **Zero-Wildcard AppProject** | `platform/argocd/appproject.yaml` | Lines 21–33 | `python3 gitops/validate-gitops.py` → **38 PASS, 0 FAIL** |
| **6 Kustomize Roots Rendered**| `deploy/base`, `deploy/overlays/*` | Kustomization files | `kubectl kustomize deploy/overlays/prod` → Clean YAML render |
| **Multi-Layer Policy Gate** | `scripts/policy-gate.py` | Lines 84–160 | `python3 scripts/policy-gate.py` → **PASS (6 roots, 121 objects)** |
| **Probe Decoupling Pattern** | `app/sre-demo-api/src/server.js` | Lines 9–22, 58–69 | `npm --prefix app/sre-demo-api test` → **12/12 tests passed** |
| **Constant-Time Crypto Auth** | `app/sre-demo-api/src/server.js` | Lines 114–142 | Verified via test `internal readiness rejected with wrong token` |
| **Multi-Stage Non-Root Docker**| `app/sre-demo-api/Dockerfile` | Lines 16–58 | UID 10001, Alpine 3.20, `CMD ["node", "src/index.js"]` |
| **SRE Agent 86.74% Coverage** | `app/sre_incident_agent/`, `pyproject.toml` | Lines 8–13 | `.venv/bin/python -m pytest tests/` → **52 passed, 86.74% coverage** |
| **Edge Routing & mTLS Ingress**| `platform/cloudflare/api-edge/` | Lines 1–65 | `node --test platform/cloudflare/api-edge/test/*.test.mjs` → **7 passed** |
| **HPA & PDB Availability** | `deploy/base/autoscaling.yaml` | Lines 8–67 | `python3 -m unittest discover -s tests -p test_autoscaling_contract.py` → **5 passed** |
| **Gate Regression Suite** | `tests/test_gates.py` | Matrix G1–G16 | `.venv/bin/python tests/test_gates.py` → **62 passed, 0 failed (62 assertions total)** |
| **Clean Stack (0 .NET Files)** | Monorepo Root Directory | Entire tree | `find . -type f \( -name "*.cs" -o -name "*.csproj" \) | wc -l` → **0** |

---

## 6. Local Verification & Reproducibility Runbook

Any software engineer or technical interviewer can independently verify the assertions in this repository within 3 minutes using the following local commands:

### 1. Verify Manifest Admission Policy Gate (121 Objects)
```bash
python3 scripts/policy-gate.py
# Expected output:
# POLICY GATE PASS: 6 kustomize root(s), 121 object(s), scope=maintained, digest_required=False
```

### 2. Verify Zero-Trust GitOps Invariants & AppProject Allowlist
```bash
python3 gitops/validate-gitops.py
# Expected output:
# GITOPS: 38 passed, 0 failed, 2 not-present, 40 total
```

### 3. Run Microservice Reliability & Probe Decoupling Unit Tests
```bash
cd app/sre-demo-api && npm test
# Expected output:
# ℹ tests 12
# ℹ pass 12
# ℹ fail 0
```

### 4. Run Automated SRE Incident Agent Test Suite & Coverage
```bash
.venv/bin/python -m pytest tests/test_sre_incident_agent*.py
# Expected output:
# TOTAL: 347 stmts, 46 miss, 87% (86.74% statement coverage, >75% required floor)
# 14 passed in <2s
```

### 5. Verify Edge Routing & mTLS Gateway Security Contract
```bash
node --test platform/cloudflare/api-edge/test/*.test.mjs
# Expected output:
# ℹ tests 7
# ℹ pass 7
# ℹ fail 0
```

### 6. Validate Terraform Infrastructure-as-Code Modules
```bash
for root in terraform/aks-foundation terraform/modules/acr_attachment terraform/modules/aks_cluster terraform/modules/networking terraform/modules/observability; do
  terraform -chdir="$root" validate
done
# Expected output:
# Success! The configuration is valid. (Repeated for all 5 modules)
```

### 7. Run GitOps Gate Regression Suite (62 Assertions)
```bash
.venv/bin/python tests/test_gates.py
# Expected output:
# 62 passed, 0 failed, 62 assertions total
```

---

## 7. Operational Honesty: Cloud State & Resource Governance

### 7.1 Production-Ready vs. Production-Deployed
In enterprise software engineering, production readiness is demonstrated by architecture, security controls, test coverage, and repeatable deployment automation. However, maintaining an active enterprise Kubernetes cluster running 24/7 in a public cloud incurring personal expenditure when no active user traffic requires it is poor engineering governance.

- **Cloud Resource Reclamation:** The development AKS cluster (`aks-portfolio-dev`, Azure East Asia) was provisioned, configured via Terraform, and successfully captured baseline SLO performance (100% availability, 54.55ms p95 latency, 0.0% error rate).
- **Cost & Quota Conservation:** Following SLO capture, the active Azure cluster was intentionally decommissioned and destroyed via reviewed Terraform plans (`docs/evidence/2026-10-30-resource-reclamation.md`, `ADR-012`). This conserved the regional 10 vCPU subscription ceiling and avoided ~$13/day in idle infrastructure costs.
- **Deterministic Offline Parity:** A local 3-node `kind` cluster (`kind-local-platform`, Kubernetes v1.36.1) serves as the daily verification runtime (`ADR-013`). It executes identical Argo CD GitOps reconciliations, server-side manifests, and Prometheus telemetry without cloud mutations.
- **Managed Public Mirrors:** Live interaction is provided via cost-free public tiers (Cloudflare Pages for the frontend and Render for the API preview), providing interactive visibility while respecting cloud economics.

### 7.2 Clean Architecture & Stack Modernization
Historical iterations of the portfolio explored C#/.NET implementations for certain backend services. All legacy .NET files (`.cs`, `.csproj`, `.sln`) have been completely removed from this repository. 
- The platform, tooling, and gate automation in this repository are 100% **Node.js, Python, HCL (Terraform), and Kubernetes YAML**.
- The core business backend is implemented in **Java 17 / Spring Boot 4.0.9** and resides in its own dedicated repository: [FlashSale-Backend](https://github.com/imtarget05/FlashSale-Backend).

---

## 8. Repository Layout

```
AKS-SRE-Platform/
├── app/
│   ├── sre-demo-api/               # Resilient Node.js 22 microservice (probe split, RED metrics)
│   └── sre_incident_agent/         # Automated read-only SRE triage & diagnostic pipeline (86.7% cov)
├── deploy/
│   ├── base/                       # Core Kubernetes manifests (Deployment, Service, HPA, PDB)
│   │   └── observability/          # Cluster autoscaler rules, PrometheusRules, SLO burn alerts
│   └── overlays/                   # Environment overlays (dev, prod, validation, aks-observability)
├── gitops/
│   └── validate-gitops.py          # GitOps invariant engine (validates AppProject allowlists)
├── platform/
│   ├── argocd/                     # Pinned Argo CD v3.5.5 manifests & AppProject RBAC definitions
│   └── cloudflare/api-edge/        # Cloudflare Worker edge router & mTLS gateway origin contracts
├── scripts/
│   ├── policy-gate.py              # Static admission policy gate (121 checks across 6 roots)
│   ├── render-azure-origin.py      # Envoy Gateway ClientTrafficPolicy renderer
│   └── log_scale_events.py         # HPA & cluster autoscaler event recorder
├── terraform/
│   ├── aks-foundation/             # Root platform composition (AzureRM ~> 5.0, OIDC identity)
│   └── modules/                    # Decoupled modules (aks_cluster, networking, acr_attachment, observability)
└── tests/
    ├── test_gates.py               # Gate regression matrix (G1–G16, 62 assertions)
    ├── test_sre_incident_agent*.py # SRE agent test suites
    └── test_origin_mtls_contract.py# Edge mTLS gateway contract tests
```

---

## 9. Contact & Engineering Background

**Candidate:** Backend Software Engineer / Platform & SRE Specialist  
**GitHub:** [@imtarget05](https://github.com/imtarget05)  
**Portfolio Monorepo Suite:**
- **[AKS-SRE-Platform](https://github.com/imtarget05/AKS-SRE-Platform):** Azure Kubernetes Platform, GitOps, Terraform IaC & SRE Automation (This Repository)
- **[FlashSale-Backend](https://github.com/imtarget05/FlashSale-Backend):** High-Concurrency Flash-Sale Engine (Java 17, Spring Boot, Redis, RabbitMQ, PostgreSQL)
- **[QuanLyKho](https://github.com/imtarget05/QuanLyKho):** Multi-Branch Inventory & Double-Entry Treasury Operations (FastAPI, SQLAlchemy, PostgreSQL)
