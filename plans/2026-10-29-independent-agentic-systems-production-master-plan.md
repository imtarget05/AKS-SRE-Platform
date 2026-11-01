# Three Independent Agentic Systems — Portfolio Production Master Plan

**Status:** Proposed execution plan. No application code, cloud resource, or identity has been changed by authoring this document.
**Purpose:** build and prove one independently owned agentic workflow in each of the three projects, then promote each project separately through evidence-based production gates.
**Projects:** FlashSale/OpsBridge (`/Users/mainguyenbinhtan/Downloads/OpsBridge`), QuanLyKho (`/Users/mainguyenbinhtan/Downloads/QuanLyKho`), and AKS-SRE-Platform (`/Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform`).

## 1. What this plan promises

This plan aims to establish tested coverage for an agreed set of important use cases, least-privilege boundaries, safe fallback behavior, and operational evidence for each project. No finite plan or eval suite can prove correct behavior for every possible future real-world input. Every promotion report must state which cases were tested, the data distribution, known gaps, measured results, and residual risks.

“Production-ready” means the project passes its business, security, reliability, privacy, cost, deployment, and operational gates on the exact code and image digest being promoted. Passing a local test suite, synthetic eval, manifest render, or one cloud smoke test alone is not production evidence.

The free-tier goal applies to a **cost-capped pilot**. It is not a promise of zero-cost production or production SLA. Cloud deployment must stop if the budget, hard quota behavior, identity, durability, or service availability cannot be demonstrated. Microsoft describes free tiers as generally lacking an SLA and recommends a paid SLA tier for production; AKS Free does not make nodes, storage, networking, databases, or inference free.

## 2. Required product and architecture decisions

### 2.1 Three independently owned systems

Each project owns its own workflow/orchestrator, 2–3 bounded agent roles, data/API adapters, identity, tool allowlist, audit trail, model/provider configuration, quota, eval casebook, deployment lifecycle, and runbooks. Agents do not call or delegate to another project's agents. No shared runtime Agent Hub or shared agent database is in the target architecture. Common engineering standards and report formats are allowed; runtime control and authorization remain project-local.

Each 2–3 role loop is sequential, bounded, and invoked only when needed. Deterministic code owns triggers, data reads, authorization, state transitions, policy gates, and writes. Model calls summarize, classify, or propose within a typed contract. An AI critic can flag problems; a deterministic verifier and authorized human decision remain authoritative.

### 2.2 Project-specific systems and first use cases

| Project-owned system | First bounded workflow | Independent roles | Allowed action in initial release |
|---|---|---|---|
| **FlashSale Order Operations Agent** in the FlashSale context of OpsBridge | Investigate one dead-lettered outbox event, return cited state and operator checks. Existing deterministic outbox/stuck-order automation remains the trigger. | Triage → Investigator → Critic/Policy | Read and recommend only. No requeue, payment cancel, order mutation, or inventory mutation. |
| **QuanLyKho Inventory Operations Agent** | Assess a submitted stocktake/adjustment request using canonical request version and inventory lines; explain risk factors and missing evidence. | Request Triage → Inventory/Discrepancy Analyst → Checker Brief/Critic | Read and recommend only. Maker/Checker remains the sole approval path; agent cannot approve, post ledger, or change inventory. |
| **AKS-SRE Incident Agent** | Investigate an SLO burn or worker error alert using verified Prometheus/Alertmanager/GitOps/runbook evidence; produce a cited incident brief. | Alert Triage → Diagnostics → Incident Critic/Brief | Read only. No `kubectl` writes, Argo sync/rollback, scaling, Terraform, or secret access. |

The role names do not require three separate always-running services or three independent model deployments. Keep one project-owned bounded workflow and invoke roles sequentially. Avoid extra model calls unless evaluation shows measurable benefit.

### 2.3 Ownership boundaries and existing shared Agent Hub

- FlashSale owns order, payment, inventory reservation, and its outbox state. Use its owner-controlled API; never access OpsBridge tables or databases directly. The first pilot targets FlashSale's API in the OpsBridge repository, **not** OpsBridge procurement/reconciliation outbox.
- QuanLyKho FastAPI + PostgreSQL is its authoritative business API. Keep the AI advisory inside QuanLyKho. Do not use the legacy Cloudflare Worker as its production business API.
- AKS-SRE-Platform is currently defined as infrastructure-only in `AGENTS.md`, while it also contains the cross-domain `apps/agent-hub`. Before implementation, make an explicit ADR decision whether the platform-owned SRE workflow is a bounded platform automation workload in this repo or a reviewed separate project. Do not silently expand the repository boundary. In either case it must be independent of the cross-domain Agent Hub.
- Treat `apps/agent-hub` as a reference/legacy project until a migration decision exists. Do not add more project adapters or deploy it as the shared runtime. Do not delete existing data or code; record parity, ownership, migration, and decommission decisions separately.
- Do not merge repository histories. The platform repo consumes immutable workload image digests and GitOps overlays; it does not own order, inventory, or business logic.

## 3. Project-specific workflow contracts

### 3.1 FlashSale Order Operations Agent

1. **Trigger:** operator requests investigation for exactly one `MessageId`, or an existing deterministic alert links to one event. Do not make LLM polling the event source.
2. **Gather:** use only signed owner endpoints `GET /internal/agent/outbox/stuck`, `/pending`, and `/{messageId}`. Capture message ID, dead-letter/processed timestamps, retry count, pending count, observation timestamp, source SHA, and evidence hash. Do not fetch payloads or secrets.
3. **Triage:** classify `DEAD_LETTERED`, `BACKING_OFF`, `ALREADY_PROCESSED`, `NOT_FOUND`, `STALE`, or `INSUFFICIENT_EVIDENCE`. Only a current dead-lettered event can receive a recovery recommendation.
4. **Investigate:** describe what metadata establishes, identify unknowns, and link read-only operator checks. Do not claim broker/root cause from event metadata alone.
5. **Critic:** verify every material claim against evidence, verify scope and freshness, and block instructions/actions. One bounded redraft maximum.
6. **Human and verify:** an authorized operator accepts/rejects the recommendation; re-read the event before closing. Changed state becomes `STALE` and requires a new run.
7. **Never call during initial release:** `POST /internal/agent/outbox/{messageId}/requeue`, bulk requeue, or any business mutation.

Implementation references: OpsBridge `src/Order.Api/Program.cs:958-1047`, `src/Order.Api/Auth/AgentRecoveryAuth.cs:8-41`, `tests/IntegrationTests/OutboxEndpointTests.cs:129-267`, and `docs/adr/017-opsbridge-bounded-context-foundation.md:14-41`. Existing stuck-order scan at `Program.cs:481-495` is deterministic automation and a possible trigger, not an LLM role.

### 3.2 QuanLyKho Inventory Operations Agent

1. **Trigger:** Maker submits a stocktake/adjustment request or an authorized Checker requests a read-only assessment. Do not trigger from chat text alone for a write operation.
2. **Gather:** load canonical request, version, location/branch, inventory lines, and relevant audit facts through QuanLyKho services. Enforce user and location scope before any model call. Minimize/redact identifying and financial fields before an external provider call.
3. **Triage:** deterministic risk and workflow checks first; classify normal, high-risk, stale-version, missing-evidence, scope violation, or policy violation.
4. **Analyze:** explain supported risk factors and discrepancies with source references. AI may add caution or raise a review priority; it cannot lower deterministic policy risk or invent a quantity/ledger fact.
5. **Critic/Checker Brief:** validate evidence references and version freshness, then prepare a concise decision brief for the Checker.
6. **Decision:** Maker/Checker rules, self-approval prevention, step-up controls, and server-side policy remain unchanged. The human Checker decides; the agent cannot approve/post/change inventory.

Implementation references: `backend/app/api/routes/ai.py:48-230`, `backend/app/services/ai.py:147-267`, `backend/app/services/ai_retrieval.py:31-145`, `backend/app/api/routes/approvals.py:33-160`, `backend/app/services/approval_controls.py:11-69`, and `backend/tests/test_ai_provider_gating.py`, `test_ai.py`, `test_business_journey_full.py`. Extend existing Copilot capability; do not build a duplicate parallel Copilot.

Required production hardening includes: replace demo/mock auth with approved issuer and provisioning, remove caller-selected provider routing in production, replace process-local rate/quota limits with a distributed or provider-enforced limit, document provider data handling/region/retention, and verify model calls do not receive unnecessary maker/reason/amount data.

### 3.3 AKS-SRE Incident Agent

1. **Trigger:** alert or operator-selected incident ID. The alert rule and SLO definition are authoritative; agent does not invent alert conditions.
2. **Gather:** read exact Prometheus/Alertmanager evidence, Kubernetes workload status/log references, current Argo revision/image digest, relevant runbook, and observation time using fixed read-only interfaces.
3. **Triage:** classify severity and affected service from alert labels and SLO policy; group related alerts by deterministic correlation rules.
4. **Diagnose:** summarize evidence, recent deployment correlation, plausible causes, uncertainty, and missing signals. A correlation is not proof of causation.
5. **Critic/Brief:** require citations and verify the runbook target and namespace. Produce an operator incident brief with read-only checks.
6. **Human response:** SRE selects and executes remediation using normal change-management controls. Agent has no write credential or shell tool.
7. **Verify:** re-read alert/health and record whether the alert resolved; do not report alert delivery as verified unless the notification path was actually observed.

Implementation references: `platform/observability/README.md:58-121`, `scripts/capture_aks_alert_cycle.py:27-133`, `docs/runbooks/runbook-sli-slo-error-budget-burn.md:21-54`, `docs/runbooks/production-release-governance.md`, `docs/runbooks/aks-30-day-slo-evidence.md`. Existing documentation records missing current 30-day production SLO evidence, metric-name reconciliation, external synthetic probe, and independent review; re-check current state before acting.

## 4. Required use-case and risk inventory

Before implementation, create a project-local matrix with one row per in-scope use case and these fields:

`use_case_id | user/persona | business outcome | trigger | canonical data source | allowed facts | decision/action | impact if wrong | permission | human approver | fallback | audit fields | eval cases | metric | owner | status`

Minimum case categories to cover (expand from repository requirements and interviews; do not assume this list is complete):

- **FlashSale:** dead-lettered event, retry/backoff, healthy event, already processed, missing event, stale/conflicting reads, duplicate request, invalid scope/identity/HMAC, outbox store unavailable, broker/provider unavailable, misleading or injected text, malformed model output, audit-store failure.
- **QuanLyKho:** valid adjustment, normal low-stock advisory, large/risky change, stale version, missing source lines, wrong location/branch, Maker self-approval, Checker other-identity approval, concurrent review, invalid/expired step-up, external provider failure/429, sensitive-data minimization, prompt injection in notes/documents, database/audit outage.
- **AKS-SRE:** real SLO burn, resolved alert, duplicate/noisy alerts, worker crash loop, rollout/Argo drift, dependency outage, missing/stale metrics, inaccessible namespace, wrong cluster/context, runbook mismatch, control-plane/cloud unavailable, no production SLO target, prompt injection in logs, unsupported remediation request, alert notification not delivered, telemetry/audit outage.

Prioritize by business impact and likelihood, with explicit severity. Every critical use case needs at least one positive, negative, stale-data, dependency-failure, and authorization case. Keep development and sealed holdout cases separate. Add sanitized historical incidents only after owner approval, data minimization, privacy/security review, and retention decisions.

## 5. Phased delivery and decision gates

All phases are sequential at the portfolio gate level. The three project designs may be documented in parallel; implementation and cloud promotion happen one project at a time. Do not skip or auto-advance a gate. Each phase is independently resumable by an AI executor.

### Phase 0 — Safe repository and cloud inventory

**Work:** read every repo's `AGENTS.md`, README, current plan/tasks, architecture/ADRs, CI, deployment overlays, current branch/ref and `git status`. Identify uncommitted/untracked user work and preserve it. Read-only inventory current cloud subscription/account, region, resources, state/backend ownership, identities, quota, bills, and free allowances. Reconcile contradictory or historical status docs with live evidence.

**Evidence:** exact repository path/ref/SHA, modified-file inventory, current cluster/resources, state owner, CI status, auth provider status, cost/quota snapshot, and any unknowns.

**Gate:** no code changes/cloud mutations until repo and cloud ownership/state are understood. Platform repo has historical evidence of cluster teardown and stale/conflicting claims; verify current state rather than assuming cluster exists.

**Do not:** run Terraform init/apply/destroy, deploy, alter subscriptions/identities, overwrite local WIP, or trust archived cloud evidence as current.

### Phase 1 — Product scope, use-case matrix, and decisions

**Work:** interview/review existing product requirements and runbooks. Fill the matrix in §4 for each project. Confirm the named first workflow and business owner. Write an ADR in each owning repo for agent boundaries, provider/data policy, role responsibilities, audit/retention, and why the runtime is project-local. Resolve the platform-repo boundary for the SRE workload before coding.

**Gate:** one approved primary workflow per project, measurable user value, failure fallback, data owner, security owner, operator/reviewer, and explicit non-goals. No generic “agent for everything” scope.

### Phase 2 — Shared assurance contract, independent runtime designs

**Work:** define only common documentation and evaluation conventions (trace/run IDs, version fields, risk taxonomy, evidence format shape, reporting template). Design separate project-local ports/adapters/workflows and storage. Inventory existing Copilots/automation and reuse only where they fit. Define API contracts, finite states, evidence TTL, tool and network allowlists, per-run limits, data retention, failure semantics, SLOs, and rollback.

**Gate:** architecture review confirms no cross-project runtime call, shared permissions, shared database, or implicit secret; deterministic code owns identity, scope, data reads, policy, state transitions, approvals, and writes.

### Phase 3 — FlashSale pilot implementation (read-only)

**Work:** execute the existing [FlashSale pilot plan](../../OpsBridge/plans/2026-10-29-flashsale-order-ops-agent-pilot.md) inside the FlashSale context. Add typed workflow, project-owned read adapter, audit persistence, three sequential roles, deterministic policy, eval suite and operator review surface. Keep provider disabled by default and no production write identity mounted.

**Gate:** all pilot tests pass on exact SHA; outbound test proves GET-only; no route can reach requeue; 100% authorization/scope negatives denied; 100% stale/missing/conflicting evidence abstains; 100% factual claims cite evidence; model/provider failure fails closed. Report measured latency/cost and human usefulness; if the sample is insufficient, keep it in pilot.

### Phase 4 — QuanLyKho agent implementation

**Work:** extend the existing risk Copilot with the bounded stocktake/adjustment assessment loop. Keep deterministic heuristic and canonical DB facts authoritative. Apply provider allowlisting, data minimization, production auth, distributed quota, audit trace and Checker-only decision path. Build its own casebook and evals.

**Gate:** exact current repo test/build checks pass; Maker cannot approve own request; only scoped Checker can decide; AI cannot lower deterministic risk or mutate/post; provider disabled/error does not block core approval; sensitive data sent to provider is approved and minimized.

### Phase 5 — AKS-SRE agent implementation

**Work:** after Phase 1 resolves repository boundary, add a platform-owned read-only incident workflow using fixed interfaces to observability, Kubernetes read APIs, Argo/GitOps revision and runbooks. Build its own casebook, audit, dashboards and runbooks. Keep `kubectl` write, Argo mutation, Terraform and secret tools unavailable to all agents.

**Gate:** exact cluster/namespace/context is validated; every output cites observed signal/runbook revision; missing SLO/evidence causes abstention; alert notification claims are only made when delivery was observed; no mutating tool or credential is present. Current SLO and cloud state must be re-verified.

### Phase 6 — Evaluation and red-team for each project

**Work:** for each agent independently run unit, contract, integration, end-to-end, adversarial, privacy, resilience, load/capacity, and recovery tests as appropriate. Use fake provider for normal CI. Run opt-in provider eval only within an enforceable quota. Use a sealed holdout and independent operator labels. Simulate prompt injection in event text, request notes, logs, and runbooks; scope confusion; malicious peer-like content; provider timeout/429; stale state; audit failure; duplicate trigger; retry storm; wrong model/version; and model/prompt/tool-policy change.

**Proposed hard release thresholds (set final values in ADR before measuring):**

- Zero unauthorized writes/tool calls. Read-only workflow uses no write-capable credential or HTTP client path.
- 100% of auth/scope/self-approval negative cases denied by deterministic authorization.
- 100% of stale, missing, conflicting, or unsupported evidence cases abstain.
- Zero fabricated entity IDs, inventory figures, event states, alert names, or citations on the sealed eval.
- 100% of material factual claims trace to source evidence; no production recommendation without valid evidence reference.
- Zero critical/high security findings unresolved; secret/PII leakage evals block promotion.
- Provider/quota/network failure remains safe and observable; no paid fallback when $0 inference is required.
- Usefulness, precision/recall, false-positive/negative, abstention, p50/p95 latency, token/cost per run, operator override, and incident recovery are reported per scenario. Do not use one portfolio-wide accuracy number to hide a weak project.
- Targets for non-safety metrics (e.g. usefulness and latency) are agreed from baseline and SLO needs before evaluating. Do not invent or retroactively loosen them to pass.

**Gate:** exact same artifacts and model/prompt/tool-policy versions that passed eval move to shadow; any material change requires the relevant evals again.

### Phase 7 — Shadow pilot and production-like drills

**Work:** deploy one project at a time to an isolated non-production or approved shadow environment. Agent reads and proposes; humans act using existing procedures. Compare its analysis to independently recorded human outcomes. Run failure drills for identity/provider outage, data source lag, DB/broker/telemetry outage, audit-store failure, restart/rollout, quota exhaustion, network policy, backup/restore where stateful, and rollback. Capture exact image digest, config, logs/traces, observed cost and environment.

**Gate:** project owner, security reviewer, SRE/operator, and product owner sign off on the evidence report; no critical safety failure; runbooks and alerts tested; recovery and rollback proven. Do not claim customer outcomes based on synthetic tests.

### Phase 8 — Cloud cost, quota, and deployment gate

**Work:** cost every component, not just inference: compute, control plane, database, Redis/broker, storage, logs/retention, egress, registry, DNS/edge, backups, secrets, monitoring, support/SLA and idle resources. Verify free quotas by exact account/region/date. Determine what happens at a quota boundary and whether hard stop exists. Validate provider privacy, residency, retention, abuse controls, data contract, rate limits and availability. Save a reviewed plan and deployment artifact.

**Gate:** actual or cost-calculator estimate reconciled with measured pilot usage; expected monthly and 2x burst scenarios fit an explicitly approved budget; hard cap/kill behavior is demonstrated, or provider is disabled at limit. If the requirement remains zero-cost plus production SLA, mark `NO-GO` if the provider/platform cannot meet both. Do not call AKS Free production-ready; Microsoft recommends AKS Standard for production SLA and Free tier still incurs underlying node/resource charges.

**Do not:** infer spend control from a budget alert alone; use free credits as a permanent cost model; deploy infra without current state/owner and required approvals.

### Phase 9 — Controlled production promotion, one project at a time

**Work:** publish immutable digest, apply reviewed GitOps/environment config, use canary or limited operator cohort, verify startup/readiness, auth, data access, dashboards, alerts, business workflow, provider quota, audit persistence and rollback. Keep agent write-free. Define owners/on-call, support hours, retention, incident response, change management, model/prompt rollback, and feature kill switch.

**Gate:** production approval records target SLO/SLA, actual cost cap, model/provider/version, accepted risks, escalation path, and go/no-go signatures. Promote next project only after previous project has a stable observation window and no unresolved safety/operational issue.

### Phase 10 — Operate, learn, and expand action authority only by separate approval

**Work:** monitor business outcomes, drift, abstention/override rate, hallucination reports, provider/model changes, cost, latency, quota, audit integrity, and SLO/error budget. Review incidents and feedback on a fixed cadence; maintain a versioned casebook from approved postmortems. Keep immediate disable/rollback procedure tested.

Any future write action requires a separate ADR, threat model, human/dual approval, exact-action hash/idempotency, owner API enforcement, independent execution verification, new eval set, rollback/recovery drill, and explicit production change approval. Do not treat successful read-only pilot as approval to mutate business data or infrastructure.

## 6. Production metrics and dashboards

Every project dashboard must separate workflow health from model quality and business outcomes:

- Workflow: starts, completions, failed, timed out, stale, abstained, retried, duplicate, and queue age.
- Safety: blocked tool requests, unauthorized/scope denials, stale-evidence stops, missing citations, policy conflicts, and audit failures.
- AI: provider/model/prompt version, request count, token/usage, provider errors/429, latency percentiles, per-run cost, quota remaining, and model-disable state.
- Human: accepted/rejected/overridden recommendations, time to review, usefulness and correction reasons.
- Business: project-specific metric from the use-case matrix (e.g. event investigation time; inventory assessment correction rate; time to SRE incident summary). Do not count AI requests as business value.

Avoid labels with high cardinality such as event IDs, user IDs, full prompt text, or raw inventory/order data. Keep sensitive content out of logs and provider traces; access to audit evidence is scoped and retained per policy.

## 7. Portfolio-wide release evidence bundle

For each project, keep a self-contained evidence package with:

1. Exact source SHA, workflow/config/prompt/model version, container digest and environment.
2. Approved use-case/risk matrix and ADR.
3. Eval dataset manifest (no sensitive raw data), results, metrics, holdout summary and known gaps.
4. Auth/scope negative tests, tool/network allowlist proof, privacy/data-flow review and security scan.
5. Integration/E2E, load, failure-drill, recovery, backup/restore and rollback results as applicable.
6. Shadow human comparison, cost/quota report, SLO/SLA and runbook links.
7. Signed release decision and open risk/owner list.

Never copy old evidence numbers forward as current. Evidence must map to the exact deployed artifact and actual environment.

## 8. Execution instructions for the AI implementing this plan

Use this as the top-level task prompt:

> Read this entire master plan and every `AGENTS.md`, README, current plan/task, ADR, test and deployment document in all three repositories before changing files. Begin at Phase 0 and report exact current refs, dirty/untracked user changes, current cloud state, state ownership, current auth and cost/quota facts. Preserve existing user changes and evidence. Do not use the shared cross-domain Agent Hub as runtime. Do not merge repository history. Keep every project’s agent, workflow, identity, tools, audit, provider config and evals independent.
>
> Implement only one phase at a time and only in the owning repository. Before each phase, present its file ownership and acceptance gate. Make the smallest change that satisfies that phase, add/update tests and documentation required by that repository, run the repository’s real verification commands, inspect the diff, and record exact outputs and SHA. Do not claim results not observed. Do not proceed past a failed gate. Do not run Terraform apply/destroy, deploy to cloud, modify subscription/identity/secret, enable paid inference, or grant write permissions unless the user explicitly approves the reviewed concrete action. Never weaken a gate to make it pass. If a project boundary or budget requirement conflicts with the design, stop that phase and report the conflict with evidence.
>
> Start with the FlashSale single-dead-lettered-event read-only pilot. After it passes its synthetic, security, and shadow gates, implement QuanLyKho’s scoped stocktake/adjustment assessment as a separate system. Then implement the AKS-SRE read-only incident workflow after resolving the platform repository boundary and verifying current cluster/observability state. Promote each system independently; no cross-project runtime coordination.

## 9. Source and current-state references

### Local project sources consulted

- FlashSale/OpsBridge: `/Users/mainguyenbinhtan/Downloads/OpsBridge/AGENTS.md`, `README.md`, `docs/adr/017-opsbridge-bounded-context-foundation.md`, `src/Order.Api/Program.cs`, `src/Order.Api/Auth/AgentRecoveryAuth.cs`, `tests/IntegrationTests/OutboxEndpointTests.cs`, and `plans/2026-10-29-flashsale-order-ops-agent-pilot.md`.
- QuanLyKho: `/Users/mainguyenbinhtan/Downloads/QuanLyKho/README.md`, `backend/app/api/routes/ai.py`, `backend/app/services/ai.py`, `backend/app/services/ai_retrieval.py`, `backend/app/api/routes/approvals.py`, `backend/app/services/approval_controls.py`, and AI/business journey tests.
- AKS-SRE-Platform: `/Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform/AGENTS.md`, `tasks/current.md`, `plans/2026-10-23-three-workload-platform-readiness.md`, `platform/observability/README.md`, `scripts/capture_aks_alert_cycle.py`, and SLO/release runbooks.
- Existing Agent Hub was inspected for patterns but is explicitly excluded as the shared runtime: `/Users/mainguyenbinhtan/Downloads/AKS-SRE-Platform/apps/agent-hub/`.

### External guidance

- Microsoft [Azure Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/) and [maturity/readiness guidance](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework).
- Microsoft [testing guidance](https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/testing) and [reliability monitoring](https://learn.microsoft.com/azure/well-architected/resiliency/monitoring).
- Microsoft [AKS production reliability guidance](https://learn.microsoft.com/en-us/azure/aks/best-practices-app-cluster-reliability) and [container-service/free-tier considerations](https://learn.microsoft.com/en-us/azure/architecture/guide/container-service-general-considerations).
- NIST [Generative AI Profile (AI 600-1)](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence).
- OWASP [AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) and [Excessive Agency risk](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/).
