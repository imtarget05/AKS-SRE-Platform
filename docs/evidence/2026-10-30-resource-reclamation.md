# AKS resource reclamation — 2026-10-30

Context: `aks-portfolio-dev`. Live read checks required sandbox network escalation. No secrets were printed.

## Completed

- `kubectl --context aks-portfolio-dev top pods -A` identified `flashsale/cpu-stress` consuming 965m CPU. Its spec had no owner reference, no data volume, and an infinite `dd /dev/zero → /dev/null` loop.
- Deleted only this diagnostic pod with `kubectl --context aks-portfolio-dev -n flashsale delete pod cpu-stress --wait=true`; exit 0. A subsequent `get pod cpu-stress --ignore-not-found` returned no object.
- Node `aks-sys-20053029-vmss000001` CPU changed from 1152m / 60% before cleanup to 222m / 11% after metrics refreshed. These are point-in-time samples, not a load benchmark or billing reduction.
- Public QuanLyKho `/api/v1/health/ready` returned HTTP 200 after cleanup. API and worker remained 1/1 Running with zero restarts.

## Dependencies and retained data

Hostname-only inspection inside both live QuanLyKho API and worker showed `DATABASE_URL` points to `postgres.flashsale.svc.cluster.local`. Therefore the flashsale namespace, Postgres StatefulSet/service/PVC must remain. QuanLyKho's own Postgres StatefulSet was already at zero replicas.

`rabbitmqctl list_queues name messages_ready messages_unacknowledged consumers` showed:

| Queue | Ready | Unacknowledged | Consumers |
| --- | ---: | ---: | ---: |
| automation.events | 0 | 0 | 1 |
| opsbridge.events.dlq | 2 | 0 | 0 |
| orders | 0 | 0 | 3 |
| opsbridge.goods-receipts.v1 | 0 | 0 | 2 |

The two dead-letter messages were preserved. Kafka topic/group listing returned no entries, but Kafka storage uses `emptyDir`; stopping it is not generally data-preserving. No StatefulSets, PVCs, application deployments, HPA, or GitOps settings were changed.

## Further reclamation boundary

The public flashsale HTTPRoute still sends traffic to order-api, opsbridge-api and payment-service. Empty queue snapshots do not prove ingestion/outbox drain. Further scale-to-zero requires an ingress maintenance plan, producer/outbox drain verification, and capture of HPA/replica rollback state. Opsbridge HPA currently enforces minimum 2, maximum 5 replicas. Flashsale Argo has manual sync and is OutOfSync/Healthy.

Current application replicas: opsbridge-api 2, order-api 2, order-worker 1, payment-service 1, redis 1; Kafka/Postgres/RabbitMQ each 1. Preserve shared Postgres even if the other services are suspended. No Azure node pool reduction was performed.

## Independent platform verification

- Parsed the corrected QuanLyKho Application YAML: `spec.source.targetRevision` is the full 40-character `350fc131421d583556bcd64674a78c7678a9d669`; that commit exists in the local QuanLyKho repository. This does not attest to live deployment of that revision.
- `python3 scripts/policy-gate.py`: PASS, 5 roots / 96 objects, digest enforcement disabled.
- `python3 -m pytest tests -q -o addopts=''`: 38 passed, 12 subtests passed in 2.09s.

These results do not establish complete production readiness.
