# Cutover Runbook — dev → validation → prod

## Prerequisites

- dev overlay green: `kubectl kustomize deploy/overlays/dev` renders exit 0, smoke test PASS.
- validation overlay green: `kubectl kustomize deploy/overlays/validation` renders exit 0.
- prod digest placeholder replaced by a signed digest (Task 2.1 done): `deploy/overlays/prod/kustomization.yaml` images uses a real SHA256 digest, not `@sha256:0000...0000`.
- `AGENT_HUB_JWT_SECRET` configured (used by agent-hub for rollback audit events).
- `INTERNAL_READINESS_TOKEN` configured (used for internal readiness probe auth).
- kubectl context is `kind-local-platform` (default, fail-closed — never Azure/prod by default).

## Step 1: Promote dev → validation

Apply the validation overlay:

```bash
kubectl apply -k deploy/overlays/validation
```

Verify:

```bash
kubectl get pods -n flashsale
kubectl get deployment sre-demo-api -n flashsale -o jsonpath='{.status.readyReplicas}/{.spec.replicas}'
curl -s -o /dev/null -w "%{http_code}" http://<validation-endpoint>/health/ready   # expect 200
```

Gate: readyReplicas == replicas and `/health/ready` returns 200 before proceeding.

## Step 2: Promote validation → prod

Apply the prod overlay:

```bash
kubectl apply -k deploy/overlays/prod
```

Verify:

```bash
kubectl get deployment sre-demo-api -n flashsale -o jsonpath='{.status.readyReplicas}/{.spec.replicas}'   # expect 3/3
kubectl get hpa sre-demo-api -n flashsale -o jsonpath='{.spec.minReplicas}/{.spec.maxReplicas}'         # expect 3/10
kubectl get deployment sre-demo-api -n flashsale -o jsonpath='{.spec.template.spec.containers[0].image}' # expect digest-pinned image
curl -s -o /dev/null -w "%{http_code}" http://<prod-endpoint>/health/ready                               # expect 200
```

Gate: 3 replicas ready, HPA min 3 / max 10, image is digest-pinned (not a mutable tag), `/health/ready` returns 200.

## Step 3: ArgoCD sync

Argo CD Apps are manual-sync. Sync the target Application:

```bash
argocd app sync <app-name>
```

Verify Application status:

```bash
argocd app get <app-name> -o json | jq '.status.sync.status, .status.health.status'
# expect: "Synced" / "Healthy"
```

Do not enable autosync during cutover. Autosync is only re-enabled after the cutover is complete and verified, per the rollback contract.

## Rollback trigger

Rollback immediately when any of the following holds:

- Any `Failed` or `Degraded` condition on the Application or its workloads (Deployment/HPA/Pod).
- Readiness flips to not-ready for more than 2 minutes (`readyReplicas < replicas` sustained).
- `/health/ready` returns non-200 or errors for more than 2 minutes.

## Rollback procedure

See `docs/rollback/rollback-contract.md`. In summary:

1. `argocd app set <app> --sync-policy manual` (dừng autosync) before touching anything.
2. Roll back to the previous known-good digest/tag from kustomization `images` history, or `git revert` of the overlay.
3. Re-apply and verify pods running, `readyReplicas == replicas`, `/health/ready` returns 200.
4. Optionally re-enable autosync.
5. Record the rollback in `audit_events` (agent-hub) with `event_type='rollback_executed'`.
