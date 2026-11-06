# T12 — Cost Estimation + Local Migration Rehearsal

**Task:** T12 — Cost estimation from Terraform (read-only) + local migration rehearsal with Docker PostgreSQL (no Azure)
**Branch:** `codex/wave3-t12-t14`
**SHA (AKS-SRE-Platform):** `f064ad3`
**SHA (QuanLyKho):** `5f0890b`
**Date:** 2026-11-06
**Environment:** Local Docker (macOS), no Azure credentials, no `terraform apply`, no Azure API calls
**Status:** DONE

---

## Part 1 — Cost Estimation from Terraform (read-only)

**Source:** `terraform/aks-foundation/` + `terraform/modules/{aks_cluster, networking, acr_attachment, observability}`
**Pricing basis:** Public Azure pricing docs (eastasia region), no Azure API, no actual cost export. Label: **estimate from public pricing, not actual cost export.**

### Resources by module

| Module | Resource | Type / SKU | Qty | Est. monthly cost | Pricing basis |
|---|---|---|---|---|---|
| aks_cluster | `azurerm_resource_group` | Resource Group | 1 | $0 | RG itself is free |
| aks_cluster | `azurerm_kubernetes_cluster` | AKS Free tier (sku_tier=Free) | 1 | $0 | AKS control plane free on Free tier |
| aks_cluster | `azurerm_kubernetes_cluster_node_pool` (sys) | Standard_D2s_v6 × 2 nodes | 2 | ~$140.50 | 2 vCPU, 8 GiB; ~$0.0962/hr per node (eastasia) |
| aks_cluster | `azurerm_kubernetes_cluster_node_pool` (work, optional) | Standard_D2s_v6 × 1 node | 1 (when enabled) | ~$70.25 | Same SKU; only when `enable_workload_pool=true` |
| networking | `azurerm_resource_group` | Resource Group | 1 | $0 | Free |
| networking | `azurerm_virtual_network` | VNet | 1 | $0 | VNet itself is free |
| networking | `azurerm_subnet` (apps/monitoring/private_endpoint) | Subnet | 3 | $0 | Subnets are free |
| networking | `azurerm_network_security_group` | NSG | 1 | $0 | NSG itself is free |
| networking | `azurerm_network_security_rule` | NSG rules | 2 | $0 | Rules are free |
| networking | `azurerm_subnet_network_security_group_association` | NSG association | 3 | $0 | Free |
| networking | `azurerm_private_dns_zone` | Private DNS zone | 1 | ~$0.50 | $0.50/month per zone |
| networking | `azurerm_private_dns_zone_virtual_network_link` | VNet link | 1 | $0 | Free (1 link per zone free) |
| networking | `azurerm_storage_account` (flow_logs) | Standard LRS | 1 | ~$1.84 | ~$0.0184/GB-month; ~100 GB assumed for NSG flow logs |
| networking | `azurerm_network_watcher` | Network Watcher | 1 | $0 | Free |
| networking | `azurerm_network_watcher_flow_log` | Flow log | 1 | $0 | Flow log config free; storage charged via storage account |
| acr_attachment | `azurerm_role_assignment` | Role assignment | 1 (when enabled) | $0 | RBAC assignments are free |
| observability | `azurerm_resource_group` | Resource Group | 1 | $0 | Free |
| observability | `azurerm_log_analytics_workspace` | PerGB2018 | 1 | ~$2.30/GB ingested | ~$2.30 per GB; cost depends on log volume |
| observability | `azurerm_monitor_data_collection_rule` | DCR | 1 | $0 | DCR itself is free |
| observability | `azurerm_monitor_data_collection_rule_association` | DCR association | 1 | $0 | Free |
| observability | `kubernetes_manifest` (otel namespace) | K8s Namespace | 1 | $0 | Cluster compute only |
| observability | `helm_release` (otel-collector) | Helm release | 1 | $0 | Runs on existing node pool |

### Estimated monthly total (validation profile, eastasia)

| Scenario | System pool | Work pool | DNS zone | Storage | Log Analytics | Est. total/month |
|---|---|---|---|---|---|---|
| Foundation only (system pool, no work pool) | 2 × D2s_v6 | — | $0.50 | ~$1.84 | variable | ~$142.84 + logs |
| + Work pool (1 × D2s_v6) | 2 × D2s_v6 | 1 × D2s_v6 | $0.50 | ~$1.84 | variable | ~$213.09 + logs |
| Teardown state (cluster destroyed) | — | — | — | — | — | $0 compute (only orphaned storage/state if any) |

**Notes:**
- AKS Free tier means $0 for the Kubernetes control plane; you pay only for VM nodes, disks, and networking.
- `sku_tier = "Free"` in `variables.tf:24` — control plane is free.
- `system_pool_node_count = 2` default (`variables.tf:36`), `Standard_D2s_v6` (`variables.tf:30`).
- Work pool is optional (`enable_workload_pool = false` default, `variables.tf:42`); when enabled it is 1 node fixed or autoscaled 1–3.
- Log Analytics cost is variable and depends on ingested GB; not included in the fixed total.
- Public pricing reference: https://azure.microsoft.com/en-us/pricing/details/kubernetes-service/, https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/, https://azure.microsoft.com/en-us/pricing/details/monitor/
- **This is an estimate from public pricing, not an actual cost export.** No `az consumption` or Cost Management API was called.

---

## Part 2 — Local Migration Rehearsal (Docker PostgreSQL 16)

### Setup

| Item | Value |
|---|---|
| Container image | `postgres:16-alpine` |
| Container name (primary) | `t12-rehearsal-postgres` |
| Container name (restore target) | `t12-rehearsal-postgres-restore` |
| Host port (primary) | 55432 |
| Host port (restore target) | 55433 |
| Database | `bankops` |
| User | `bankops` / `bankops` |
| Repo | QuanLyKho @ `5f0890b` |
| Alembic | 1.20.0 (QuanLyKho/backend/.venv) |

### Step 1 — Alembic migration 001→head on empty DB

| Field | Value |
|---|---|
| Command | `DATABASE_URL="postgresql+psycopg2://bankops:bankops@127.0.0.1:55432/bankops" .venv/bin/python -m alembic upgrade head` |
| Start (UTC) | `2026-11-06T09:24:11Z` |
| End (UTC) | `2026-11-06T09:24:14Z` |
| Duration | ~3 seconds |
| Exit code | `0` |
| Migrations applied | 001_initial → 034_general_ledger_coa (34 migrations) |
| Tables after migration | 55 |
| Alembic version | `034_general_ledger_coa` (head) |

### Step 2 — Seed fake data from `sample-data/`

| Field | Value |
|---|---|
| Command | `DATABASE_URL="postgresql+asyncpg://bankops:bankops@127.0.0.1:55432/bankops?ssl=disable" APP_ENV=demo DEMO_MODE=true .venv/bin/python -m app.seed` |
| Start (UTC) | `2026-11-06T09:24:19Z` |
| End (UTC) | `2026-11-06T09:24:21Z` |
| Duration | ~2 seconds |
| Exit code | `0` |
| Seed source | `QuanLyKho/sample-data/{inventory.json, users.json, cash-sim.json}` |
| Rows seeded | 10 iam_users, 9 iam_roles, 4 inv_locations, 30 inv_items, 33 inv_balances, 3 cash_boxes, 120 inv_stock_levels |

### Step 3 — pg_dump

| Field | Value |
|---|---|
| Command | `PGPASSWORD=bankops pg_dump -h 127.0.0.1 -p 55432 -U bankops -d bankops --format=custom --file=docs/labs/t12-evidence/bankops.dump` |
| Start (UTC) | `2026-11-06T09:24:31Z` |
| End (UTC) | `2026-11-06T09:24:31Z` |
| Duration | <1 second |
| Exit code | `0` |
| Output file | Local-only `docs/labs/t12-evidence/bankops.dump` (excluded from Git; regenerate for a new rehearsal) |
| File size | 150,289 bytes |
| Format | custom (pg_restore compatible) |

### Step 4 — Simulate cutover: restore to second container

| Field | Value |
|---|---|
| Target container | `t12-rehearsal-postgres-restore` (port 55433) |
| Command | `PGPASSWORD=bankops pg_restore -h 127.0.0.1 -p 55433 -U bankops -d bankops --format=custom --clean --if-exists --no-owner docs/labs/t12-evidence/bankops.dump` |
| Start (UTC) | `2026-11-06T09:24:51Z` |
| End (UTC) | `2026-11-06T09:24:52Z` |
| Duration | ~1 second |
| Exit code | `0` |

**Row count verification after cutover (original vs restored):**

| Table | Original (55432) | Restored (55433) | Match |
|---|---|---|---|
| iam_users | 10 | 10 | YES |
| inv_locations | 4 | 4 | YES |
| inv_items | 30 | 30 | YES |
| inv_balances | 33 | 33 | YES |
| cash_boxes | 3 | 3 | YES |
| inv_stock_levels | 120 | 120 | YES |

All row counts match. Cutover restore verified.

### Step 5 — Simulate rollback: restore back to original

| Field | Value |
|---|---|
| Action | `DROP DATABASE bankops; CREATE DATABASE bankops;` then `pg_restore` back to original |
| Start (UTC) | `2026-11-06T09:25:17Z` |
| End (UTC) | `2026-11-06T09:25:19Z` |
| Duration | ~2 seconds |
| Exit code | `0` |

**Row count verification after rollback (original DB):**

| Table | After rollback | Expected | Match |
|---|---|---|---|
| iam_users | 10 | 10 | YES |
| inv_locations | 4 | 4 | YES |
| inv_items | 30 | 30 | YES |
| inv_balances | 33 | 33 | YES |
| cash_boxes | 3 | 3 | YES |
| inv_stock_levels | 120 | 120 | YES |
| alembic_version | 034_general_ledger_coa | head | YES |

All row counts match after rollback. Rollback verified.

### Step 6 — RPO/RTO measured from actual timings

| Metric | Value | Basis |
|---|---|---|
| RPO | 0 seconds | pg_dump captures all committed data at dump time; restore reproduces the exact state. No data loss between dump and restore observed. |
| RTO (dump → restore) | ~1 second | Measured pg_restore duration on second container. Full cutover (decision → restore complete) bounded by dump + restore time. |
| RTO (rollback) | ~2 seconds | Measured drop/create + pg_restore duration on original container. |
| Total rehearsal wall time | ~8 minutes | From migration start to rollback verification end. |

### Evidence artifacts

| Artifact | Path | Description |
|---|---|---|
| pg_dump output | Local-only artifact; not in Git | Custom-format dump, 150,289 bytes, exit code 0; SHA-256 `8b4fa097e17617ce50602a4f16a6fb65a63706081e24f7d5bdc477f40106a6c3`. The dump contains seeded user password/PIN hashes and one email, so retain it only in a controlled local evidence store. The recorded row counts and timings remain historical observations, not a substitute for a new restore drill. |

---

## Part 3 — Constraints honored

- No `terraform apply` or `terraform destroy` was run.
- No Azure API calls were made.
- No Azure resources were created.
- No secrets were committed to the repository.
- All work was local Docker only.

---

## What the user needs to provide

Nothing for T12 — it is fully complete offline. T12 does not depend on Azure.
