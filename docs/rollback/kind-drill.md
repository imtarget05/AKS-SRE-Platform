# Reproducible rollback drill for the repo workload

The `Kind rollback drill` workflow builds `app/sre-demo-api`, starts a disposable
kind cluster, deploys two replicas, checks `/health/ready`, applies a deliberately
missing image, waits for Kubernetes to report `ErrImagePull` or
`ImagePullBackOff`, then runs `kubectl rollout undo`. The script verifies the
original image, both ready replicas, and HTTP 200 after recovery. The workflow
uploads `kind-rollback-evidence` with timestamps, cluster state, pod status,
events, and the measured rollback duration. A failure leaves `status: failed`
in `result.json`; the workflow does not turn it green.

This is an isolated kind test of the repository's Node workload and Kubernetes
rolling update behavior. It does not prove Azure AKS, Argo CD autosync handling,
customer traffic, or zero dropped requests under continuous load. The
[Argo CD rollback contract](rollback-contract.md) remains the runbook for a
GitOps-managed environment. Do not reuse the old FlashSale `order-api` drill
scripts as evidence for this repo's current workload.

Local reproduction requires Docker, kind, kubectl, and Python 3:

```bash
docker build -t sre-demo-api:local-drill app/sre-demo-api
kind create cluster --name sre-rollback --wait 120s
kind load docker-image sre-demo-api:local-drill --name sre-rollback
python3 scripts/kind_rollback_drill.py --context kind-sre-rollback \
  --image sre-demo-api:local-drill
kind delete cluster --name sre-rollback
```

Use the workflow artifact for a run tied to a specific Git commit. A local
reproduction on 2026-11-19 passed; see the [timestamped evidence and reproduction
commands](../evidence/local-kind-rollback-2026-11-19/README.md). The earlier Docker
unavailability on 2026-11-18 no longer describes the current workstation.
