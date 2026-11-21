# Workload failure triage (kind or AKS)

Use the exact context, namespace, Deployment and image digest from the incident record. Record the UTC start time, alert, affected endpoint, commit SHA, and image reference before changing anything. The commands below are read-only until the rollback step. For Azure, follow [production release governance](production-release-governance.md) before any mutation.

```sh
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get deploy,pods -o wide
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events --sort-by=.lastTimestamp
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout history deploy/"$DEPLOYMENT"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get deploy "$DEPLOYMENT" -o jsonpath='{.spec.template.spec.containers[*].image}'
```

| Symptom | Check | Decision |
| --- | --- | --- |
| HTTP 502 | Check ingress/Gateway route, ready endpoints, pod readiness, and upstream error logs. Compare error rate before and after the release. | If the new revision has no ready endpoints or error rate rises after release, stop promotion and use the reviewed rollback procedure. |
| `CrashLoopBackOff` | `describe pod`, `logs --previous`, restart reason, probe configuration, and recent config changes. | Fix configuration if a rollback cannot restore a working dependency; otherwise roll back the failing revision. |
| `OOMKilled` | Inspect `lastState`, memory limit, usage trend, request volume, and HPA status. | Restore the last healthy revision if the increase began with this release; otherwise investigate capacity and request shape before raising limits. |
| Database timeout | For a workload that actually uses a database, compare readiness, connection-pool saturation, database health and network policy. The repo's `sre-demo-api` does not use a database. | Do not blame the platform from a 502 alone. Escalate to the owning application/database team with timestamps and connection evidence. |

For the local kind drill, the [rollback evidence](../evidence/local-kind-rollback-2026-11-19/README.md) shows `ErrImagePull` and `rollout undo` restoring two ready replicas. It does not measure full outage recovery. In an authorized environment, capture the pre-change image reference, perform the reviewed rollback, then verify the restored reference, ready replicas, HTTP response and error-rate trend. Record detection time, rollback start, restoration time, and the sampled traffic window separately.
