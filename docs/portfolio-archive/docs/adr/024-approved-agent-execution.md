# ADR 024 — Agent Hub được thực thi tác vụ sau Human in the Loop

**Status:** Partially Implemented & Verified in Isolated Environment. Supersedes the read-only execution decision in ADR 023.
- **Pilot Implementation:** Single-event OpsBridge Outbox Recovery (`REPLAY_STUCK_OUTBOX`) is fully implemented and verified via owner API `/internal/agent/outbox/{message_id}/requeue` using HMAC-SHA256 request signing, dual-control human approval (`approver != requester`), and state reconciliation (`UNKNOWN` on dropped response).
- **Target Integrations:** Retail adjustment posting, QuanLyKho stock adjustment, and Platform Argo rollbacks remain target roadmap items awaiting domain-specific dual-control endpoints.

## Business problem

Read-only investigation stops before the expensive operational step: an operator still has to reconstruct the evidence, find the right command, execute it and confirm that the system actually recovered. The Agent Hub should be able to carry an approved action to completion while preserving the owner system's business invariants and audit trail.

## Decision

Agent Hub gains a **scoped executor**, not a general shell, database connection or unrestricted cloud credential. The LLM may propose an action from a versioned command catalog. The executor can call the owner system's command API or Argo CD API only when a human with the required role has approved the **exact** action intent. The owner system rechecks authorization, resource version, business preconditions and idempotency before changing state.

The workflow is:

```text
Incident / scheduled trigger
  → read scoped evidence from owner APIs + platform signals
  → deterministic verifier + Agent proposal
  → typed ActionIntent and policy/risk evaluation
  → human reviews exact target, parameters, evidence, impact and recovery plan
  → signed, short-lived approval bound to intent hash, actor, scope and expiry
  → Agent executor obtains scoped identity and calls allowlisted owner command API
  → owner applies transaction / audit / outbox or Argo change
  → Agent reads post-state, verifies invariant and persists outcome / receipt
```

**Approval is not a side effect.** A human approval merely permits one bounded execution attempt. A rejected, expired, revoked or changed intent cannot execute. An ambiguous response is reconciled by idempotency key and owner-side status before retry.

## Action contract

`ActionIntent` is immutable after submission and contains:

- `intent_id`, `run_id`, `command_type`, owner service and allowlisted endpoint;
- tenant/outlet/branch/namespace, entity ID, expected record version or GitOps revision;
- canonical parameter hash, evidence hashes and source versions, risk level, reason;
- idempotency key, expiry, maximum attempts, expected postcondition and compensation/runbook reference.

`Approval` binds `intent_hash`, approver identity and role, scope, timestamp, expiry and decision. Approval cannot be reused for another target, changed parameters, a stale source version, or a second execution. For money/stock/order effects, the owner's maker–checker policy applies independently of the Agent Hub.

`ExecutionReceipt` contains approval ID, intent ID, owner command ID, idempotency key, before/after version, result, audit reference and verification result. The Hub keeps an append-only transition log and correlation ID across evidence, approval, owner command and post-state checks.

## Initial command catalog and authority

| Owner | Approved agent action | Required owner-side gate | Status |
| --- | --- | --- | --- |
| Retail Finance | Start reconciliation; create an adjustment draft; post a separately approved adjustment only after a ledger-specific dual-control API exists | Outlet scope, amount/ledger version, idempotency, separate maker/checker, MySQL transaction and audit | **Target**; no money-posting tool exists today |
| FlashSale / OpsBridge | Replay a specified dead-letter outbox event via HMAC signed `/internal/agent/outbox/{id}/requeue` | SRELead / SecurityOfficer role, requester ≠ approver, exact message ID and DeadLetteredAt timestamp binding, single-event outbox compare-and-swap, idempotency key in `OutboxRecoveryCommands` | **IMPLEMENTED (Pilot)**; verified end-to-end against PostgreSQL with crash/retry drills |
| QuanLyKho | Submit a stocktake for review; apply an adjustment after a checker approval | Branch/location scope, FEFO and stock balance, maker ≠ checker, voucher version, single posting | **Target integration**; Hub executor does not exist |
| AKS-SRE-Platform | Roll back one allowlisted Argo application to a reviewed revision; scale within a bounded range | Namespace/AppProject RBAC, deployment revision, maintenance policy, health and post-rollout checks | **Target**; no generic `kubectl`/`terraform` tool |

Cloud `terraform apply/destroy` remains a separate human-reviewed saved-plan/environment workflow; the Agent may prepare the plan and request approval but cannot substitute its own approval for that gate.

## Execution state machine

```text
EVIDENCE_READY → ACTION_DRAFTED → POLICY_CHECKED → AWAITING_APPROVAL
  → APPROVED → EXECUTING → VERIFYING → SUCCEEDED
  ↘ REJECTED / EXPIRED / REVOKED / STALE / DENIED / FAILED / UNKNOWN
```

`UNKNOWN` is mandatory when the owner may have committed but the response was lost. The executor first queries the owner command status by idempotency key; it never repeats a non-idempotent call blindly. A changed entity version or evidence hash returns `STALE` and requires a new intent and new approval. Failed post-state verification blocks a success claim and opens an incident.

## Security and reliability controls

1. **Two enforcement points:** Hub policy before approval and owner authorization/business rules at command execution. UI-only checks are insufficient.
2. **Least privilege:** executor uses short-lived workload identity scoped to one command family and owner endpoint; no browser token or static admin bearer token.
3. **No raw generated commands:** the model cannot submit arbitrary HTTP path, SQL, shell, `kubectl`, `terraform` or script text. It selects a versioned command type with validated schema.
4. **Durable coordination:** intents, approvals, execution attempts and receipts need a shared transactional store with concurrency control; the current single-replica SQLite/PVC prototype is insufficient for a multi-replica release.
5. **Replay safety:** unique intent/approval/owner command IDs, deterministic idempotency keys, compare-and-swap on source version, bounded retry and status reconciliation.
6. **Audit and privacy:** redact PII/secrets from evidence and logs; persist actor, approver, executor identity, source versions, payload hash, timestamps and owner audit reference.
7. **Risk-tiered HITL:** every mutation requires explicit approval; high-impact financial, stock or infrastructure actions require the owner's separate dual-control or protected environment gate.

## Pilot Verification (OpsBridge Outbox Recovery)

The OpsBridge single-event recovery pilot (`REPLAY_STUCK_OUTBOX`) is implemented and verified:
1. Hub extracts single dead-letter outbox event (`messageId`, `deadLetteredAt`) and drafts typed `ActionIntent`.
2. Action requires dual-control human approval (`approver != requester`, role `SRELead` or `SecurityOfficer`). Self-approval returns 403.
3. Executor computes HMAC-SHA256 signature (`X-Agent-Timestamp`, `X-Agent-Signature`) over method, path, timestamp, and body hash with shared secret.
4. Owner endpoint `/internal/agent/outbox/{messageId}/requeue` executes atomic compare-and-swap on `deadLetteredAt` and inserts `OutboxRecoveryCommands` row with unique `IdempotencyKey`.
5. Only the target event is requeued; concurrent or sibling dead-letter events remain unchanged.
6. When network response is dropped after commit, Hub transitions to `UNKNOWN`. Subsequent retry with same idempotency key recovers the durable receipt (`already_applied`) without double-execution.

## Relationship to ADR 023

ADR 023's read adapters, evidence provenance, deterministic verifier and abstain policy remain useful. Its blanket **zero-write-tools** rule is replaced by this approved, typed execution boundary. The current Agent Hub code still implements the older read-only model; the diagrams for ADR 024 show the **target state**, not a delivered runtime capability.
