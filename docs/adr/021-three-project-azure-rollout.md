# ADR-021: Staged Azure rollout for the three-project portfolio

- Status: **PROPOSED — local design only; no Azure changes approved by this ADR**
- Date: 2026-11-05
- Scope: `AKS-SRE-Platform`, `FlashSale-Backend`, and `QuanLyKho`

## Context

The portfolio spans a platform repository, a Java payment-service repository,
and an inventory/operations application. They have independent owners and data
boundaries; they are not one production system.

The live Azure baseline was checked before writing this ADR:

- AKS `aks-portfolio-dev` is `Running` in `eastasia`, with a public API endpoint
  and three `Standard_D2s_v6` nodes (two system, one user).
- `payment-service` is running at 2/2 replicas. `/healthz` and `/health/live`
  returned HTTP 200.
- PostgreSQL and Kafka workloads are also present in the `default` namespace.
- The repository worktrees already contain uncommitted changes. This rollout
  does not replace or revert those edits.

This is a live validation environment, not evidence that the portfolio meets
production or banking-compliance requirements. In particular, FlashSale
simulates payment outcomes and QuanLyKho models financial operations; neither
should be represented as processing real money or as a compliant banking
system.

## Cost gate

The selected monthly ceiling is **USD 100**, including the existing AKS
baseline. The Azure Retail Prices API was queried for East Asia Linux
`Standard_D2s_v6` on-demand compute at approximately USD 0.139 per node-hour.
At 730 hours per month:

```text
3 nodes × USD 0.139/hour × 730 hours = approximately USD 304/month
```

This is compute only; it excludes managed disks, load balancers, networking,
logging, storage, and data services. Discounts, taxes, and actual billing can
differ. The current AKS compute estimate alone exceeds the selected ceiling.
The Azure Cost Management CLI command was unavailable on the workstation, so
this is not a statement of actual invoiced spend.

Azure budgets are notifications and forecasts, not hard spending caps; crossing
a threshold does not stop resources. Before creating any additional cloud
resources, the owner must either raise the approved ceiling or explicitly
approve a separate cost-reduction/teardown phase. This ADR does not authorize
stopping or deleting the live cluster.

## Decisions

1. **Use AKS as the primary runtime for the portfolio pilot.** Do not create
   parallel VMs or App Services merely to claim those technologies. Document
   the alternatives; deploy them only when a distinct workload requirement
   justifies their cost and operating model.
2. **Preserve workload ownership.** The platform repository owns shared Azure
   infrastructure, identity, policies, and observability. FlashSale and
   QuanLyKho each own their image, deployment manifests, release workflow, and
   database boundary. They must not share application databases or secrets.
3. **Keep the existing public AKS environment classified as validation.** A
   production design must review API-server access, ingress, identity, network
   isolation, backups, audit, and recovery before any promotion. No in-place
   networking or cluster mutation is approved here.
4. **Keep PostgreSQL authoritative for existing application transactions.**
   Introduce Oracle and Azure Cosmos DB only behind explicit adapters and
   separately tested use cases. Do not dual-write payments to PostgreSQL,
   Oracle, and Cosmos DB. Use an outbox/event contract for any derived
   projection; define consistency, retention, recovery, and ownership first.
   Verify Oracle service availability, licensing, region, and pricing before
   proposing a deployment.
5. **Add gRPC as an internal service contract, not as a replacement for public
   HTTP APIs.** Define versioned `.proto` files, generated-code checks, health
   checks, deadlines, authentication, and TLS/mTLS requirements before
   deployment. Public access remains through the existing HTTP edge unless a
   separately reviewed use case requires otherwise.
6. **Keep CI/CD on the existing GitHub Actions baseline for now.** Prefer
   short-lived Azure federated identity (OIDC), environment approvals,
   least-privilege access, pinned image digests, and a reviewed Terraform plan.
   Do not add a second Azure DevOps/GitLab/Jenkins pipeline without a concrete
   ownership or organizational requirement.
7. **Use Azure services by purpose, not by checklist.** Plan Blob Storage for
   encrypted off-cluster backups and recovery evidence; use managed disks only
   for state that cannot move to a separately operated managed database. Plan
   Azure Monitor/Log Analytics with an explicit ingestion and retention cap.
   Neither is approved for provisioning by this ADR.
8. **Do not claim compliance from infrastructure presence.** Define data
   classification, access reviews, key rotation, audit retention, backup
   restore tests, incident response, and applicable regulatory scope before a
   production claim. The current demo payment flow does not process cardholder
   data or real payments.

## Staged rollout and exit gates

| Phase | Scope | Exit criteria before the next phase |
|---|---|---|
| 0 — Baseline and cost | Reconcile Azure inventory, Terraform remote state, repository evidence, current AKS workload ownership, and a real cost export. Add budget alerts only after verifying recipients and billing scope. | Approved budget covers the measured baseline and proposed services; `terraform plan` is reviewed; no conflicting state or uncommitted edits are overwritten. |
| 1 — Platform safety | Design private/control-plane access, ingress/WAF, workload identity and Key Vault integration, network policies, namespace quotas, image provenance, and log retention. | Security review and cost estimate pass; apply requires separate approval for this phase. |
| 2 — FlashSale pilot | Move from the current `default` namespace only through a reviewed migration plan; isolate dependencies, secrets, database access, probes, resource limits, and rollback. Add internal gRPC contract and tests before exposing it. | Deployment, integration, authentication, backup/restore, and rollback checks pass on a non-production environment. |
| 3 — QuanLyKho pilot | Deploy API/worker with its own PostgreSQL and secrets. Treat Airflow scheduler/executor as a separately costed workload; validate DAGs and recovery before enabling schedules. | App-level authorization, data isolation, migrations, backup restore, and scheduled-ingestion checks pass. |
| 4 — Additional data stores | Prototype Oracle and Cosmos adapters separately. Define which system owns each record and test idempotency, retries, outbox/projection rebuild, and failure recovery. | Documented use cases and separate cost approval for each service; no dual-write in the payment transaction path. |
| 5 — Production decision | Review availability targets, capacity, upgrade strategy, disaster recovery, security/compliance evidence, support ownership, and cost envelope across all three projects. | Explicit production go/no-go approval; this ADR alone is not a production release approval. |

No phase after 0 is authorized to mutate Azure by this ADR. Terraform apply,
Kubernetes deployment, database provisioning, and cluster stop/delete each need
an explicit approval for their specific scope.

## Rollback and safety

- Do not change the running payment service or its dependencies during design.
- Every later rollout must have a versioned image, pre-deployment health checks,
  a documented rollback target, and a post-rollback health check.
- Database schema changes must use backward-compatible expand/migrate/contract
  steps and a tested restore path; do not promise rollback by reversing a
  destructive migration.
- Never store secrets in this repository, manifests, plans, build logs, or
  chat. Use workload identity and a managed secret store.
- Keep public API exposure, firewall changes, cluster upgrades, and data-store
  migrations as separately reviewed operations.

## References

- [AKS best practices](https://learn.microsoft.com/en-us/azure/aks/best-practices)
- [Azure Cost Management budgets](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)
- [Azure Retail Prices API](https://prices.azure.com/)
- [Platform workload-isolation decision](019-platform-scope-and-workload-isolation.md)
- [Current Terraform roots and apply rules](../../terraform/README.md)
