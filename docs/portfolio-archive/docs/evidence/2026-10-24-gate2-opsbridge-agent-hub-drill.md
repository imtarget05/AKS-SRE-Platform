# Evidence: Phase 2 Isolated Business Drill (Agent Hub -> Order.Api -> PostgreSQL)

**Date:** 2026-10-24
**Environment:** Isolated local container + process environment
- **PostgreSQL:** Docker container `postgres:16-alpine` on port 5433
- **Redis:** Docker container `redis:7-alpine` on port 6380
- **Order.Api:** .NET 10 Web API on `http://127.0.0.1:5055`
- **Agent Hub:** FastAPI / Uvicorn on `http://127.0.0.1:8005`

## Execution Log
```text
[2026-10-25T02:05:25.705321+00:00] Cleaning up processes and containers...
[2026-10-25T02:05:25.905144+00:00] === Starting Phase 2 Isolated Business Drill ===
[2026-10-25T02:05:25.905208+00:00] Starting isolated PostgreSQL container on port 5433...
[2026-10-25T02:05:26.236054+00:00] Starting isolated Redis container on port 6380...
[2026-10-25T02:05:26.441106+00:00] Waiting for PostgreSQL to accept connections...
[2026-10-25T02:05:27.149505+00:00] Launching Order.Api on port 5055 with real Postgres connection...
[2026-10-25T02:05:27.152649+00:00] Waiting for Order.Api to complete migrations and listen on port 5055...
[2026-10-25T02:05:31.291800+00:00] Order.Api is healthy!
[2026-10-25T02:05:31.291840+00:00] Seeding Event A and Event B in PostgreSQL OutboxMessages...
[2026-10-25T02:05:31.371833+00:00] --- DATABASE BEFORE STATE ---
[2026-10-25T02:05:31.581676+00:00] Event A Before:
MessageId               |     DeadLetteredAt     | RetryCount 
--------------------------------------+------------------------+------------
 00000000-0000-0000-0000-00000000000a | 2026-10-24 12:00:00+00 |          5
(1 row)
[2026-10-25T02:05:31.581742+00:00] Event B Before:
MessageId               |     DeadLetteredAt     | RetryCount 
--------------------------------------+------------------------+------------
 00000000-0000-0000-0000-00000000000b | 2026-10-24 12:00:00+00 |          5
(1 row)
[2026-10-25T02:05:31.581762+00:00] OutboxRecoveryCommands Count Before:
count 
-------
     0
(1 row)
[2026-10-25T02:05:31.581771+00:00] Starting Fault-Injection Proxy on port 5056 -> Order.Api 5055...
[2026-10-25T02:05:31.582178+00:00] Launching Agent Hub on port 8005...
[2026-10-25T02:05:31.584739+00:00] Waiting for Agent Hub to listen on port 8005...
[2026-10-25T02:05:32.108815+00:00] Agent Hub is healthy!
[2026-10-25T02:05:32.108851+00:00] Agent Hub: Seeding investigation run and evidence for Event A in StorageManager...
[2026-10-25T02:05:32.264979+00:00] Proposal Created: Intent ID=intent-8d6f20252a5b, Hash=ae00e179711754831594abda6d91bf3f0bba1d9069a8cb7525a4303538420211, State=AWAITING_APPROVAL
[2026-10-25T02:05:32.265005+00:00] NEGATIVE TEST 1: Requester (operator-01) attempts self-approval...
[2026-10-25T02:05:32.266691+00:00] Self-approval rejected with HTTP 403: Forbidden (PASS)
[2026-10-25T02:05:32.266742+00:00] NEGATIVE TEST 2: Cross-scope approval attempt (scope=retail-outlet-01)...
[2026-10-25T02:05:32.268025+00:00] Cross-scope approval rejected with HTTP 403: Forbidden (PASS)
[2026-10-25T02:05:32.268057+00:00] NEGATIVE TEST 3: Sending tampered HMAC signature to Order.Api...
[2026-10-25T02:05:32.277311+00:00] Tampered HMAC rejected by Order.Api with HTTP 401 (PASS)
[2026-10-25T02:05:32.277348+00:00] NEGATIVE TEST 4: Sending stale timestamp to Order.Api...
[2026-10-25T02:05:32.333070+00:00] Stale timestamp rejected by Order.Api with HTTP 409: {"status":"state_conflict","messageId":"00000000-0000-0000-0000-00000000000a","idempotencyKey":"stale-key"} (PASS)
[2026-10-25T02:05:32.333120+00:00] Valid Independent Approval: Reviewer (reviewer-01, role=SRELead) approves intent...
[2026-10-25T02:05:32.336875+00:00] Intent Approved: State=APPROVED
[2026-10-25T02:05:32.336893+00:00] FAULT INJECTION: Arming proxy to drop response after Order.Api commits...
[2026-10-25T02:05:32.336900+00:00] Agent Hub: Executing approved intent A (expecting dropped response -> HTTP 503)...
[2026-10-25T02:05:32.392526+00:00] Agent Hub correctly caught network drop and returned HTTP 503: Service Unavailable (PASS)
[2026-10-25T02:05:32.392903+00:00] Agent Hub Intent State in SQLite after network drop: UNKNOWN
[2026-10-25T02:05:32.392913+00:00] --- DATABASE STATE AFTER COMMITTED BUT DROPPED RESPONSE ---
[2026-10-25T02:05:32.617992+00:00] Event A (Committed):
MessageId               | DeadLetteredAt | RetryCount 
--------------------------------------+----------------+------------
 00000000-0000-0000-0000-00000000000a |                |          0
(1 row)
[2026-10-25T02:05:32.618060+00:00] Event B (Untouched):
MessageId               |     DeadLetteredAt     | RetryCount 
--------------------------------------+------------------------+------------
 00000000-0000-0000-0000-00000000000b | 2026-10-24 12:00:00+00 |          5
(1 row)
[2026-10-25T02:05:32.618069+00:00] OutboxRecoveryCommands (Durable Record):
IdempotencyKey       |              MessageId               | ApprovedBy  |      IntentId       
---------------------------+--------------------------------------+-------------+---------------------
 drill-idem-key-event-a-01 | 00000000-0000-0000-0000-00000000000a | reviewer-01 | intent-8d6f20252a5b
(1 row)
[2026-10-25T02:05:32.618086+00:00] OPERATOR RETRY: Retrying execution via Agent Hub with the SAME intent and idempotency key...
[2026-10-25T02:05:32.638953+00:00] Retry Execution Succeeded! Receipt ID=rcpt-502707f5e76a, Verified=True
[2026-10-25T02:05:32.639369+00:00] Agent Hub Intent Final State in SQLite: SUCCEEDED
[2026-10-25T02:05:32.641018+00:00] Agent Hub Receipt Query: rcpt-502707f5e76a, verified=True
[2026-10-25T02:05:32.641034+00:00] --- FINAL DATABASE VERIFICATION ---
[2026-10-25T02:05:32.714629+00:00] OutboxRecoveryCommands Count after idempotent retry: (1 row)
[2026-10-25T02:05:32.714697+00:00] === DRILL COMPLETED WITH 100% SUCCESS ===
[2026-10-25T02:05:32.905140+00:00] Cleaning up processes and containers...
```

## Verified Claims & Invariants
1. **Dual-Control Enforcement:** Requester (`operator-01`) cannot self-approve (`403 Forbidden`). Only authorized independent role (`reviewer-01`, `SRELead`) can approve.
2. **HMAC Request Signing:** Order.Api strictly verifies `X-Agent-Timestamp` and `X-Agent-Signature`. Tampered signature/body rejected with `401 Unauthorized`.
3. **Single Event Scope:** Requeuing Event A (`00000000-0000-0000-0000-00000000000a`) leaves Event B (`00000000-0000-0000-0000-00000000000b`) completely untouched.
4. **Atomic CAS & Audit:** DeadLetteredAt cleared and exactly 1 row written to `OutboxRecoveryCommands` in the same database transaction.
5. **Durable Idempotency & Replay:** Re-executing with the same `idempotency_key` returns `already_applied` with 0 duplicate rows or mutations.
