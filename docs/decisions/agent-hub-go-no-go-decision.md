# Agent Hub Go / No-Go Production Architecture Decision Paper

## 1. Executive Summary & Verdict

- **Date:** 2026-10-26
- **System:** `apps/agent-hub` within AKS-SRE-Platform / Multi-Repo Portfolio
- **Review Panel:** SRE Lead, Platform Architect, Security Officer, Core Backend Maintainers
- **Final Verdict:**
  - ✅ **GO (Approved for Staging & Read-Only Pilot):** Incident Triage, Cross-Repo Evidence Correlation, and SRE Copilot (ADR-023).
  - 🛑 **NO-GO (Halted for Production Workloads):** Autonomous State Mutation, Automated Dead-Letter / Outbox Requeue, and Unsupervised Infrastructure Changes (ADR-024).

---

## 2. Background & Strategic Context

Agent Hub was introduced to assist SREs and store managers by collecting multi-repo telemetry across:
- `OpsBridge` (.NET / PostgreSQL / RabbitMQ)
- `QuanLyKho` (Python / FastAPI / PostgreSQL)
- `Retail-Finance` (Java / Spring / MySQL Ledger)
- `AKS-SRE-Platform` (Kubernetes, Argo CD, Envoy Gateway, Prometheus)

During incident scenarios (e.g., outbox dead letters, inventory reconciliation mismatches, shift count discrepancies), operators previously had to manually query multiple databases, logs, and dashboards.

Two architectural paradigms were proposed:
1. **ADR-023 (Read-Only Invariants):** Agent Hub acts strictly as an investigative sidecar querying allowlisted read endpoints with scope tokens (`user_token`, `scope_id`). No write tools.
2. **ADR-024 (Autonomous Execution):** Agent Hub directly invokes mutation endpoints (e.g. `/api/v1/outbox/requeue`, database corrections, or pod restarts) after automated LLM policy evaluation.

---

## 3. Stakeholder Evaluation Matrix

| Domain | Review Criteria | ADR-023 (Read-Only Sidecar) | ADR-024 (Autonomous Mutation) | Assessment |
|:---|:---|:---:|:---:|:---|
| **Security & IAM** | Risk of privilege escalation, prompt injection, cross-scope leakage | **LOW** (Scope tokens validated by target domain, 0 write tools) | **CRITICAL** (Indirect prompt injection in log data could trigger unwanted transactions) | 🛑 ADR-024 Rejected |
| **Financial Ledger Integrity** | Double spending, non-deterministic adjustments | **ZERO IMPACT** (Read-only) | **UNACCEPTABLE** (Ledger mutations require deterministic human dual-control) | 🛑 ADR-024 Rejected |
| **SRE / Platform Operations** | Mean Time to Detect (MTTD), Mean Time to Resolve (MTTR) | **HIGH IMPROVEMENT** (Automates multi-system evidence synthesis in <5s) | **HIGH RISK OF CASCADE** (Automated requeue during broker partition causes thundering herd) | ✅ ADR-023 Approved |
| **Cost & Latency** | LLM API token consumption, SLA impact | **PREDICTABLE** (Triggered on-demand by SREs during active incident triage) | **UNBOUNDED** (Autonomous loops could drain API budgets during continuous flapping) | ✅ ADR-023 Approved |

---

## 4. Key Invariants for the Approved Read-Only Mode (ADR-023)

1. **Zero Mutation Tools:** The Agent Hub code (`apps/agent-hub`) must never register tools with HTTP methods `POST`, `PUT`, `PATCH`, or `DELETE` targeting domain business state.
2. **Scope Token Forwarding:** Every read request dispatched by an adapter must carry the operator's authenticated bearer token and explicit branch/outlet identifier (`X-Scope-Id`).
3. **Deterministic Evidence Verification:** All model inputs are wrapped in an `EvidenceEnvelope` verified by SHA-256 hashing. If an adapter experiences a timeout or authentication failure, the agent must **abstain** rather than hallucinate root causes.
4. **Human Decision Exclusivity:** The final action (such as invoking `POST /api/v1/outbox/requeue` in OpsBridge or approving a stocktake adjustment in QuanLyKho) must be executed explicitly by a human operator in the respective system's dedicated UI.

---

## 5. Decision Sign-off

- **Platform & SRE Lead:** *Approved (Read-Only pilot on staging cluster)*
- **Security & Compliance:** *Approved with Zero-Write Invariant enforced via network policy and IAM role boundaries*
- **Application Engineering Leads (OpsBridge & QuanLyKho):** *Approved*
