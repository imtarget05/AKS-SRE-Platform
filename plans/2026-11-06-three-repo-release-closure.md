# Three-repo release closure — 2026-11-06

This plan uses the current cloud state. The owner confirmed `GO` for the portfolio demo and `HOLD` for production. A checked owner declaration is not test evidence; production remains HOLD until the applicable gates are verified and the owner signs a separate production decision.

## Current checkpoint

| Repository | Proven now | Open release gate |
| --- | --- | --- |
| AKS-SRE-Platform | CI `pr-gate` and SBOM succeeded at `c1baf58`; 3 AKS nodes Ready; Azure monthly USD 100 alert budget exists. | Argo CD is Synced at old revision `7633cad` but Degraded; Prometheus and Alertmanager Pending; placeholder FlashSale image; no production telemetry/rollback proof. |
| QuanLyKho | CI succeeded at `4e812ba`; Render Docker service live and liveness 200; empty login returns 422. The separate native Python staging build now succeeds with Python 3.11.11; source pin is in PR #19. | Native staging runtime fails closed without `BANKOPS_SIGNING_KEY`; valid login, database migration/restore and 21 cloud UAT journeys on a pinned candidate are unverified. |
| FlashSale-Backend | Java CI succeeded at remote `469ee7d`; preview PostgreSQL and Redis resources exist. PR #20 passed CI and was merged. PR #21 now records owner-approved portfolio demo scope with production HOLD. | Latest Render preview deploy at `469ee7d` failed because PostgreSQL host resolves as `postgres`; RabbitMQ/OIDC configuration, payment E2E, restore and rollback are unverified. |

## Ordered tasks and proof

1. **Lock scope and ownership.** FlashSale is demo payment and the owner accepted portfolio demonstration only. Name cost/state and UAT owners; pin a candidate SHA that exists on remote `main`. Proof: signed decision matching that candidate SHA and explicit scope, with unchecked gates left unchecked.
2. **Rotate exposed credentials.** Revoke the Cloudflare token, Render key, deploy hooks, GitHub PAT and Sonar token that appeared in chat; replace them in their actual consumers. Do this in account dashboards without copying values into the repository or evidence. Proof: owner-recorded rotation timestamps and a successful least-privilege test for each integration, with no values in logs.
3. **Repair FlashSale preview.** Use the existing preview PostgreSQL and Redis resources. Set the service's JDBC host, user/password and Redis settings from their approved secret sources; provision/configure RabbitMQ and an approved OIDC issuer/audience. Do not use the Compose hostname `postgres` or demo JWT signing in the production profile. Proof: Render deploy `live` at pinned SHA, `/health/live` and dependency readiness 200, then authenticated payment/idempotency/broker E2E with negative controls.
4. **Close QuanLyKho staging.** Choose the live Docker service as the candidate or create a distinct staging Docker service only if isolation is needed. Run valid login and all 21 named MVP journeys against API/UI on approved real devices, with actor, before/after data and negative cases. Proof: per-journey evidence at the same API/UI SHA and tested DB backup/restore.
5. **Close AKS runtime.** Remove the placeholder workload or publish an immutable real image; reconcile Argo CD to the candidate revision. Capacity-plan monitoring so Prometheus and Alertmanager schedule without violating system-pool isolation or the agreed cost ceiling. Proof: Synced/Healthy, metrics query with actual data, delivered alert fault drill and measured rollback/restore.
6. **Release decision.** Re-run affected CI/security checks on final SHAs and pin image digests. Named owners review the three evidence sets independently. Proof: explicit GO/HOLD/NO-GO for each repo; production deploy only for a GO with all mandatory gates PASS. A portfolio demo acceptance does not imply production readiness.

## Scope decisions

- A Render database already exists for FlashSale preview; creating another one is unnecessary.
- The live QuanLyKho path is Render Docker. Do not create a subscription-wide Azure Contributor service principal merely to satisfy a skipped legacy Container Apps job. If Azure deployment is later chosen, define a resource-group scope and purpose first.
- Azure's USD 100 monthly budget sends alerts; it is not a hard cost cap. Identify the state owner and export destination before new paid resources or cluster scaling.
