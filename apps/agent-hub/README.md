# Agent Hub: Bounded Investigation Service

This service investigates four business domains: retail-finance, order-failure, voucher-check, and incident. Its execution commands are allowlisted and scoped to tenant boundaries.

## Flow and invariant

1. An authenticated SRE starts an investigation for outbox-stuck-events in a given cluster. The read adapter calls HMAC-protected endpoints and returns event IDs and dead-letter timestamps, without event payloads.

2. The same caller proposes an intent with one UUID and `expected_dead_lettered_at`. The Hub requires a current, intact evidence record containing that exact pair. The intent hash binds the run, requester, scope, event, version, and idempotency key.

3. A different user with `SRELead` or `SecurityOfficer` role and the same scope approves the exact hash with a reason. Approval is recorded before execution.

4. An SRE executes the intent. The Hub signs a single-event GET and POST with a session HMAC key. The owner transactionally clears only that row's dead-letter state and writes `OutboxRecoveryCommands` with a unique idempotency key. A stale version or mismatched retry returns 409.

5. The Hub reads the event again and stores a receipt. If the owner response was lost, the intent becomes `UNKNOWN`; retrying the same intent/key asks the owner for its durable result. The command cannot be redirected to the bulk requeue endpoint.

## Local verification

From this repository root:

```bash
ENVIRONMENT=test PYTHONPATH=apps/agent-hub python3 -m pytest apps/agent-hub/tests -q
kubectl kustomize kubernetes/apps/agent-hub >/dev/null
```

From the Agent Hub repository root:

```bash
poetry run pytest tests -q
```

## Deployment contract

`kubernetes/apps/agent-hub` is opt-in. Before applying it, provision `agent-hub-secret` in the `agent-hub` namespace with `jwt-secret`, `read-bearer-token`, and `quanlykho-jwt-key`. Provision the same recovery HMAC value as `flashsale-secrets/agent-recovery-hmac-key` in the appropriate namespace. Never store these values in Git or logs. A durable workload identity and narrow read-only service authorization are required before a production claim.

The manifest currently uses `agent-hub:local`, SQLite on a single PVC, and one replica. Before promoting to AKS: publish a digest-pinned image, replace local SQLite with a highly available store and migration/backup path, configure managed secrets and identity, verify network policy/TLS, and run a real cross-service failure/recovery drill. Do not label this pilot `PRODUCTION_READY`.
