# Azure Cost Management query evidence

- **Captured:** `2026-11-06T09:23:58Z`
- **Scope:** current Azure subscription, Month-to-date
- **Query:** `ActualCost`, aggregated by `ResourceGroupName` and `ServiceName`, currency USD
- **Budget resources found:** none
- **Cost Management exports found:** none

The read-only Cost Management query returned the following rows:

| Resource group | Service | Cost (USD) |
|---|---|---:|
| `mc_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | Virtual Machines | 42.059100 |
| `mc_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | Storage | 9.201729 |
| `mc_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | Virtual Network | 0.959165 |
| `mc_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | Azure DNS | 0.192116 |
| `mc_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | Bandwidth | 0.000242 |
| `mc_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | Load Balancer | 0.000000 |
| `rg-aks-platform-dev` | Azure Kubernetes Service | 3.677990 |
| `rg-aks-platform-dev` | Key Vault | 0.000006 |
| `rg-aks-tfstate` | Storage | 0.000048 |
| `rg-flashsale` | Container Registry | 0.860774 |
| `rg-portfolio-prod` | Azure Container Apps | 0.540612 |
| `rg-portfolio-prod` | Container Registry | 0.860774 |
| **Total returned** | | **58.352554** |

Azure still reports charges under the former AKS node resource group even though the cluster and both AKS resource groups were verified absent after teardown. Cost Management data can lag resource deletion; these rows should not be interpreted as proof that the cluster is still running. The total is a month-to-date Cost Management result, not a closed invoice or a guaranteed final bill.

The subscription has no budget or scheduled Cost Management export configured. No export destination was added: the only existing storage account is the Terraform state account, and it was intentionally not reused for billing data. A dedicated export destination and notification recipient are still needed to complete the recurring budget/export setup.

This query is evidence of current reported spend, not a spending cap. Azure budgets notify but do not stop resources. Before creating another AKS validation cluster, retain a short teardown window and verify spend again.

## Follow-up after T13 teardown

- At `2026-11-06T12:13Z`, the subscription budget was verified as `$100/month`, with actual-cost notifications at 80% and 100% and forecast notification at 100%. A budget is a notification mechanism, not a spending cap.
- ActualCost query retries at `2026-11-06T12:13:34Z` and `2026-11-06T12:15:24Z` returned HTTP 429 (`Too many requests`). A retry at `2026-11-06T12:24:01Z` succeeded and returned **$58.471605 USD month-to-date** across 16 resource-group/service rows. There was no row for `rg-aks-validation-t13`; this is not proof of zero cost because billing data can lag. The query result is saved in [`post-teardown ActualCost JSON`](./2026-11-06-actual-cost-after-t13-teardown.json); request identifiers were removed, while the result columns and rows were retained.
- A read-only Consumption Usage Details query at `2026-11-06T12:17:39Z` for `2026-11-06` returned no matching records for `rg-aks-validation-t13`; the filtered CLI output is saved in [`consumption usage response`](./2026-11-06-consumption-usage-after-t13.json). This is consistent with billing-data delay and does **not** establish zero cost.
- The previous successful snapshot above was captured at `2026-11-06T09:23:58Z`, before the temporary T13 AKS/ACR were created. The later month-to-date total includes other subscription resources and cannot be attributed to this run. Refresh after billing data has had time to post.
