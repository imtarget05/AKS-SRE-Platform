# ArgoCD Rollback Contract

## Rule 1 — Dừng autosync before ANY rollback

Before performing a rollback, disable ArgoCD autosync on the target Application. Never roll back while autosync is enabled: autosync can re-apply the bad version mid-rollback, causing a race and a failed or partial rollback.

```bash
# Option A: argocd CLI
argocd app set <app-name> --sync-policy manual

# Option B: patch the Application manifest
kubectl patch application <app-name> -n argocd --type merge -p '{"spec":{"syncPolicy":{"automated":null}}}'
```

Confirm autosync is off before proceeding:

```bash
argocd app get <app-name> -o json | jq '.spec.syncPolicy.automated'
# expect: null
```

## Rule 2 — Rollback target

Roll back to the previous known-good digest/tag:

- From `images` history in the overlay `kustomization.yaml` (e.g. restore the prior `digest` or `newTag`), OR
- `git revert` of the overlay commit that introduced the bad image.

```bash
# Example: restore previous digest in prod overlay (edit then apply)
kubectl apply -k deploy/overlays/prod
```

Never roll back to `latest` or an unverified mutable tag in prod.

## Rule 3 — Verify after rollback

After re-applying the known-good version, verify:

```bash
kubectl get pods -n flashsale -l app=sre-demo-api
# expect: all Running, READY 1/1

kubectl get deployment sre-demo-api -n flashsale -o jsonpath='{.status.readyReplicas}/{.spec.replicas}'
# expect: readyReplicas == replicas

curl -s -o /dev/null -w "%{http_code}" http://<endpoint>/health/ready
# expect: 200
```

Only after verification passes, optionally re-enable autosync:

```bash
argocd app set <app-name> --sync-policy automated
```

## Rule 4 — Audit record

Record every rollback in `audit_events` (agent-hub):

```sql
INSERT INTO audit_events (event_type, actor, target_app, target_env, reason, created_at)
VALUES ('rollback_executed', '<actor>', '<app-name>', '<env>', '<reason>', NOW());
```

`event_type` must be exactly `rollback_executed`. This requires `AGENT_HUB_JWT_SECRET` to be configured for agent-hub to accept the audit write.

## Summary

| Step | Action |
|------|--------|
| 1 | `argocd app set <app> --sync-policy manual` (dừng autosync) |
| 2 | Restore previous good digest/tag or `git revert` the overlay |
| 3 | `kubectl apply -k <overlay>` and verify pods/replicas/`/health/ready` |
| 4 | Optionally re-enable autosync |
| 5 | Insert `audit_events` row with `event_type='rollback_executed'` |
