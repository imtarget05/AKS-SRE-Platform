# Azure assessment smoke evidence

- **Captured:** 2026-11-05 15:46 UTC
- **Environment:** Azure validation AKS; read-only smoke tests only
- **Cluster:** `aks-portfolio-dev`, `eastasia`, resource group
  `rg-aks-platform-dev`
- **Managed resource group:** `MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia`
- **Test target:** FlashSale Java `payment-service`
- **Data handling:** No payment was created, no load/chaos test was run, and no
  Kubernetes or Azure resource was changed by this assessment.

## Results

| Scenario | Expected | Observed | Result |
|---|---|---|---|
| AKS control plane | Running and provisioned | `Running`, `Succeeded`; Kubernetes 1.36; three Ready nodes | PASS |
| Payment deployment replica count | 2 desired, 2 ready | 2 desired, 2 ready | PASS |
| Payment deployment rollout condition | Progressing / rollout complete | `Progressing=False`, `ProgressDeadlineExceeded`; `kubectl rollout status` exceeded its progress deadline because an older ReplicaSet timed out | FAIL |
| External liveness `/healthz` | HTTP 200 | 10/10 HTTP 200; mean 92.7 ms, max 167.6 ms | PASS |
| External liveness `/health/live` | HTTP 200 | 10/10 HTTP 200; mean 94.3 ms, max 135.5 ms | PASS |
| Payment read authorization | Unauthenticated GET returns 401 | `GET /api/payments/evidence-readonly-probe` returned HTTP 401 | PASS |
| PostgreSQL deployment readiness | One ready replica | 1/1 ready; no PVC or PV was present in the cluster | PASS, ephemeral-storage risk |
| Kafka deployment readiness | One ready replica | 0/1 ready; pod in restart backoff, 15 restarts at capture | FAIL |
| Workload isolation for the other portfolio apps | Their workloads are present on this cluster | No QuanLyKho or platform GitOps/observability workload was present | NOT DEPLOYED |

The HTTP checks were sequential, low-volume GET requests. The authorization
check used a synthetic path and no credential; it did not read or modify a
payment record.

## Assessment

The public FlashSale health endpoints are reachable and basic unauthenticated
access to the protected payment-read endpoint is rejected. This is not a
production acceptance: the API is exposed through a public HTTP load balancer,
the deployment has a failed progress condition, Kafka is unavailable, and the
PostgreSQL workload has no persistent volume. The successful health responses
do not prove the full payment flow or its dependencies.

This assessment does not test throughput, payment writes/idempotency,
failover, recovery, backups, gRPC, Oracle, Cosmos DB, QuanLyKho, or platform
GitOps/monitoring. These scenarios require an isolated test dataset and/or
additional deployed workloads; do not run them against this shared validation
cluster without a reviewed plan.

## Teardown boundary

The assessment itself was read-only. The cluster teardown was performed later
on 2026-11-05 after owner approval and PostgreSQL backup. Deleting the cluster
removed its public payment API and Kubernetes workloads. No PVC/PV was present,
so PostgreSQL pod data was treated as ephemeral; the verified local dump is
the preserved database backup. Kafka was also running without a PVC and was
not backed up; the owner explicitly accepted Kafka data loss for teardown.

### PostgreSQL backup

- **Database:** `FlashSaleDb`
- **Backup:** custom-format `pg_dump`, stored outside all repositories on the
  local FileVault-encrypted disk. File permissions are `0600`; containing
  directory permissions are `0700`.
- **Integrity:** `pg_restore --list` passed; archive SHA-256 was rechecked.
- **Contents:** schema and table data were included. No row contents or database
  credentials were copied into this evidence.

Kafka could not be backed up during this run: its only broker was not Ready,
had exited with code 1, and had 21 restarts at the time of the check. No Kafka
PVC or other volume mount was present. The container command formats Kafka
storage using a newly generated cluster ID on each start; therefore the current
deployment does not provide durable broker storage. Do not assume Kafka topics
or messages are recoverable from the PostgreSQL dump.

The reviewed Terraform plan deleted exactly four resources: the AKS cluster,
its user node pool, `rg-aks-platform-dev`, and the AKS-only `AcrPull` assignment
on the shared ACR. Terraform applied the plan successfully (0 added, 0 changed,
4 destroyed). Post-destroy checks found the cluster and both AKS resource
groups absent; `rg-flashsale`, ACR `acrflashsalep6`, `rg-aks-tfstate`, and
`rg-portfolio-prod` remained present. `terraform state list` returned no
tracked resources. See the [teardown runbook](../runbooks/azure-teardown-runbook.md)
for the execution record.

No separate HTTP request was made to the former public service endpoint after
teardown. This evidence does not claim that the endpoint was independently
probed after deletion.
