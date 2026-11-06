# Temporary AKS validation evidence

- **Date:** 2026-11-06 (UTC)
- **Purpose:** Capture live Azure AKS infrastructure, workload scheduling, in-cluster HTTP, and Kubernetes rollout-undo evidence.
- **Subscription:** `Azure subscription 1` (identifier omitted)
- **Region:** `eastasia`
- **Cluster:** `aks-portfolio-dev`, resource group `rg-aks-platform-dev`
- **Kubernetes:** AKS version `1.36`, node version `v1.36.5`
- **AKS tier:** `Free`
- **Infrastructure source revision:** `3540b21bb3ec553399d3cf1d5c3838cb364a4c3e`, with the two Terraform edits described below applied in the worktree.

This was a short-lived validation cluster. It was destroyed after evidence capture. It is not a production-readiness or application-release acceptance.

## Provisioning and cost boundary

The Singapore preflight returned `NotAvailableForSubscription` for `Standard_D2s_v6` at both Location and Zone scope. The owner selected East Asia instead. A fresh SKU query there returned `Restrictions=[]`; the regional and Dsv6-family quota queries each showed `0/10` vCPUs in use/limit.

The reviewed Terraform plan contained exactly three creates and no changes or destroys:

1. Resource group `rg-aks-platform-dev`
2. AKS cluster `aks-portfolio-dev`
3. Temporary user node pool `work`

The cluster had two `Standard_D2s_v6` system nodes and one `Standard_D2s_v6` user node. It did not attach the shared ACR or create application databases, brokers, ingress, monitoring, or other shared resources.

The East Asia Linux retail price observed for `Standard_D2s_v6` was **$0.139 per node-hour**, or about **$0.417/hour** for the three nodes. The AKS tier was Free. This is a compute estimate, not the final billed amount; disks and networking may incur additional charges, and billing data may post later. No final usage-cost record was available at teardown.

The Terraform module defaulted to AKS `Standard` tier despite the repository ADR specifying `Free`. The root module now exposes `sku_tier` and defaults it to `Free`, then passes it to the AKS module. `terraform fmt -check` and `terraform validate -no-color` passed before the apply.

## Live observations

| Check | Expected | Observed | Result |
|---|---|---|---|
| AKS provisioning | Running / Succeeded | `Running`, `Succeeded` | PASS |
| AKS management tier | Free | `Free` | PASS |
| Cluster feature flags | OIDC issuer and Workload Identity enabled | Both `true` | PASS |
| Node pools | Two system nodes and one workload node | `sys`: 2; `work`: 1; all pool provisioning states `Succeeded` | PASS |
| Kubernetes nodes | All nodes Ready | 3/3 `Ready`, version `v1.36.5` | PASS |
| Test workload | Deployment available on user pool | `nginx:1.27.5-alpine`, 1/1 ready on `work` node | PASS |
| In-cluster service request | HTTP 200 | ClusterIP service returned HTTP 200 | PASS |
| Rollout undo | Deployment healthy after undo | Synthetic environment-only revision rolled back; 1/1 ready and HTTP 200 afterward | PASS |

The probe used a temporary NGINX deployment and a temporary curl pod. The service was internal (`ClusterIP`); no application endpoint was exposed publicly. The probe did not deploy or test the FlashSale payment service.

The first in-cluster HTTP probe completed at `2026-11-06T08:15:51Z`. The rollout-undo probe also completed successfully before teardown.

## Teardown and final inventory

A fresh destroy plan contained exactly three destroys and no creates or changes. Applying that saved plan reported **0 added, 0 changed, 3 destroyed**.

Post-teardown checks at `2026-11-06T08:22:42Z` found:

- `az aks list` returned no AKS clusters in the subscription.
- `rg-aks-platform-dev` did not exist.
- AKS-managed resource group `MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` did not exist.
- Terraform remote state contained no resources.
- The temporary kubeconfig and saved plan files were removed.
- Shared ACR and other resource groups were not in the destroy plan.

## Scope and limitations

This evidence verifies a live AKS control plane, node readiness, scheduling on the user pool, an internal HTTP request, and a synthetic Kubernetes rollout undo. It does **not** prove:

- FlashSale application behavior, payment authorization, idempotency, or dependency health
- ACR image pull or end-to-end Workload Identity token exchange (only the AKS feature flags were checked)
- Load, security, alerting, backup/restore, disaster recovery, or production rollback
- Final Azure billed cost

Production readiness remains **NO-GO** until the applicable release gates are rerun on the same candidate SHA and the remaining application, security, operations, cost, and owner-approval evidence is supplied.

## Addendum: FlashSale live AKS validation (T13)

- **Captured:** 2026-11-06 (UTC)
- **Source SHA:** `0eb8f518a531ccdc86294e1a41236c54c531c325`
- **Azure region:** `eastasia`
- **Validation resource group:** `rg-aks-validation-t13`
- **AKS:** `aks-validation-t13`, Free tier, Kubernetes `1.36`, two `Standard_D2s_v6` nodes
- **ACR:** `acrflashsalevalidation.azurecr.io`, Basic, admin user disabled; retained after cluster teardown
- **Current image:** `sha256:da0223892f59394f2c512bdae5c3f520514950625b22c3d393f2081960d3f1d3`, tag `t13-0eb8f51-20261106`; OCI revision label matched the source SHA
- **Rollback image:** `sha256:873ec4622c0336466d05fa8bad6ef9a012edd8bf9cfa0da6c8947ca147c92009`, tag `t13-rollback-873ec462`; the old image had no OCI revision label

The Azure server-side Kustomize dry run passed. The validation overlay enabled the Java demo and Mongo audit profiles and deployed a temporary MongoDB dependency with restricted pod security and ephemeral storage. WiredTiger cache was set to `0.25 GB` (the lower `0.125 GB` value caused MongoDB 7.0.5 to reject startup). The final workload inventory was MongoDB `1/1`, payment service `2/2`, PostgreSQL `1/1`, RabbitMQ `1/1`, and Redis `1/1`; all six pods were Ready. Services remained `ClusterIP`; the application was not exposed publicly. A temporary localhost-only port-forward and generated validation credentials were removed after the run.

| Live check | Result |
|---|---|
| Health/readiness and login | PASS |
| Successful payment and replay with the same idempotency key | PASS |
| Conflicting payload with the same key | HTTP 409, PASS |
| Decline and timeout cases | PASS |
| Outbox delivery and Mongo audit projection | First smoke: 3/3 published and projected; post-rollback smoke: 1/1 |
| Rollback | Rolled back from `873ec462…` to `da022389…`; payment service returned to 2/2 Ready |
| Post-rollback health, readiness, login, payment, and audit | PASS |
| Azure Monitor metric alert | Fired at `2026-11-06T11:54:20Z` after Ready pods fell below 6; resolved at `2026-11-06T12:02:18Z` after recovery |

The alert used a one-minute evaluation/window and threshold `kube_pod_status_ready < 6` in namespace `validation`. It had **no action group**: firing/resolution was observed in Azure Monitor, but email/on-call delivery was not tested. No Log Analytics workspace or KQL query was used.

The metric alert was deleted and the AKS delete command returned exit code 0. At the final inventory around `2026-11-06T12:12Z`, `aks-validation-t13` and its managed node resource group were absent; `rg-aks-validation-t13` contained only the retained ACR. The remaining `aks-portfolio-dev` cluster was not modified. Azure Activity Log recorded the validation cluster delete request as accepted at `2026-11-06T12:09:18Z`.

The subscription budget is `$100/month`, with actual-cost notifications at 80% and 100% and a forecast notification at 100%; it is a notification, **not** a spending cap. A post-teardown ActualCost query at `2026-11-06T12:24:01Z` returned `$58.471605 USD` month-to-date across the subscription, but no row for `rg-aks-validation-t13`; Consumption Usage Details also returned no matching record. This does not prove zero cost for the validation resources because billing data may lag teardown. See [`cost-management evidence`](./2026-11-06-cost-management-query.md) and its sanitized [ActualCost response](./2026-11-06-actual-cost-after-t13-teardown.json).

The digest-pinned Azure demo deploy, API/event flow, metric-alert state transition, rollback, teardown, and post-teardown cost query checks passed. Azure has not yet posted a cost row attributable to this validation resource group. This run does not prove action-group delivery, Log Analytics/KQL, load, production security, backup/restore, disaster recovery, or production rollback. T12 remains partial and production/T14 remains **NO-GO** pending the outstanding gates and owner sign-off.
