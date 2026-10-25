# Agent Hub: one bounded OpsBridge recovery pilot

This service investigates four domains. Its only executable command in this pilot is `REPLAY_STUCK_OUTBOX` for **one** OpsBridge `MessageId`. OpsBridge PostgreSQL remains the authority for the event state and the recovery audit. The Agent Hub stores the investigation, the reviewed intent hash, the independent human decision, and the execution receipt.

## Flow and invariant

1. An authenticated SRE starts an `order_failure` investigation for `outbox-stuck-events` in `ops-cluster-01`. The read adapter calls HMAC-protected `GET /internal/agent/outbox/stuck` and `pending`. The owner returns event IDs and dead-letter timestamps, without event payloads.
2. The same caller proposes an intent with one UUID and `expected_dead_lettered_at`. The Hub requires a current, intact evidence record containing that exact pair. The intent hash binds the run, requester, scope, event, version, and idempotency key.
3. A different user with `SRELead` or `SecurityOfficer` role and the same scope approves the exact hash with a reason. Approval is recorded before execution.
4. An SRE executes the intent. The Hub signs a single-event GET and POST with `OPSBRIDGE_AGENT_HMAC_KEY`. The owner transactionally clears only that row's dead-letter state and writes `OutboxRecoveryCommands` with a unique idempotency key. A stale version or mismatched retry returns 409.
5. The Hub reads the event again and stores a receipt. If the owner response was lost, the intent becomes `UNKNOWN`; retrying the same intent/key asks the owner for its durable result. The command cannot be redirected to the bulk `/api/outbox/requeue` endpoint.

## Local verification

From this repository root:

```bash
ENVIRONMENT=test PYTHONPATH=apps/agent-hub python3 -m pytest apps/agent-hub/tests -q
kubectl kustomize kubernetes/apps/agent-hub >/dev/null
```

From the OpsBridge repository root:

```bash
dotnet test tests/IntegrationTests/FlashSale.IntegrationTests.csproj
dotnet test tests/UnitTests/FlashSale.UnitTests.csproj
bash scripts/validate-manifests.sh
```

The Python owner HTTP tests use `MockTransport`; the .NET integration suite uses Testcontainers PostgreSQL, Redis, and RabbitMQ. This is **not** a live cross-service cluster test or an AKS readiness result.

## Deployment contract

`kubernetes/apps/agent-hub` is opt-in. Before applying it, provision `agent-hub-secret` in the `agent-hub` namespace with `jwt-secret`, `opsbridge-agent-hmac-key`, `opsbridge-read-bearer-token`, and `quanlykho-jwt-key`. Provision the same recovery HMAC value as `flashsale-secrets/agent-recovery-hmac-key` in the OpsBridge namespace. Never store these values in Git or logs. The bearer token is used only by the existing order/saga read adapter; it must be issued and rotated by the OpsBridge owner. A durable workload identity and narrow read-only service authorization are still required before a production claim. The QuanLyKho adapter still depends on a shared signing key and needs its own identity boundary.

The manifest currently uses `agent-hub:local`, SQLite on a single PVC, and one replica. Before promoting to AKS: publish a digest-pinned image, replace local SQLite with a highly available store and migration/backup path, configure managed secrets and identity, verify network policy/TLS, and run a real cross-service failure/recovery drill. Do not label this pilot `PRODUCTION_READY`.
