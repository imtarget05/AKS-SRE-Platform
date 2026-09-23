# Azure Portfolio Teardown — Pre-Destroy Inventory (Phase A, READ-ONLY)

Date: 2026-09-23 · Author: operator session (P03)

> **PRE-DESTROY INVENTORY ONLY** — this document is a frozen snapshot taken
> *before* any cleanup, not a record of cleanup.
>
> **AZURE NOT MUTATED** — no resource was created, changed, started, stopped or
> deleted. All commands used were read-only (`list`/`show`).
>
> **AZURE TEARDOWN NOT EXECUTED** — nothing in this file implies that the
> portfolio's Azure resources have been destroyed. As of this date they still
> exist (AKS cluster `Stopped`).

Command family: `az * list/show` / `az account show` (read-only).

Sanitization: no subscription ID, tenant ID, object/principal ID, credential, key
or state file content appears in this document. The operator account name is
recorded only as `<operator-account>`.

## 0. Subscription context

| Field | Value |
|---|---|
| Subscription display name | `Azure subscription 1` |
| State | `Enabled` |
| Identity model | Entra ID, single user (Owner at subscription scope) |
| Locks | `az lock list` → **empty** (no lock blocks a future destroy) |

## 1. Resource groups (7 total — the pasted teardown plan knew only 4)

| Resource group | Classification | Notes |
|---|---|---|
| `rg-aks-platform-dev` | **DELETE** (portfolio) | holds `aks-portfolio-dev` |
| `MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | **DELETE** (portfolio, AKS-managed) | node group; removed when the cluster is deleted |
| `rg-flashsale-release` | **DELETE** (portfolio) | ACR + GitHub OIDC release identity |
| `rg-flashsale-data-protection` | **DELETE after export** (portfolio) | off-host backup storage |
| `rg-flashsale-tfstate` | **DELETE LAST** (portfolio) | shared Terraform backend |
| `NetworkWatcherRG` | **KEEP** | Azure-managed (`NetworkWatcher_eastasia`); not portfolio-owned, not billable, auto-recreated |
| `rg-apexinspect-demo` | **UNKNOWN** | contains **zero resources**; not declared in the teardown plan → per its own rule, destruction STOPS until ownership is confirmed |

## 2. Resources in scope (13 total in the subscription)

| Resource | Type | RG | State |
|---|---|---|---|
| `aks-portfolio-dev` | managedClusters | rg-aks-platform-dev | `powerState: Stopped`, k8s 1.36.4, OIDC + Workload Identity enabled, **no user pool** |
| `aks-sys-26564277-vmss` | virtualMachineScaleSets | MC_… | capacity **0** (deallocated ⇒ no compute burn) |
| `kubernetes` | loadBalancers | MC_… | Standard LB, Succeeded |
| `fe417fa2-…` (redacted) | publicIPAddresses | MC_… | static, `20.187.184.211` |
| `aks-portfolio-dev-agentpool` | userAssignedIdentities | MC_… | cluster node identity |
| `aks-agentpool-39419008-nsg` / `aks-vnet-39419008` | networkSecurityGroups / virtualNetworks | MC_… | AKS-managed networking |
| `acrflashsalep6` | containerRegistry | rg-flashsale-release | **Standard** SKU, `adminUserEnabled: false` → tier has a standing charge even with no pulls |
| `id-flashsale-github-release` | userAssignedIdentities | rg-flashsale-release | GitHub OIDC release identity |
| `stflashsalebackup` | storageAccounts | rg-flashsale-data-protection | off-host backup target |
| `stflashs3ctfbk01` | storageAccounts | rg-flashsale-tfstate | Terraform state backend |

**Verified absent (corrects the plan's cost assumptions):** `az disk list` in the
MC resource group → **no managed disks**, `az snapshot list` → none. So "managed
disks keep billing" does **not** apply to this subscription. Residual burn is
ACR Standard + 2 storage accounts + 1 static public IP; there is **no node
compute charge** (VMSS capacity 0).

## 3. Terraform backend ownership (the plan's most dangerous gap)

`stflashs3ctfbk01` / container `tfstate` is **shared by three roots**, not one:

| Root (path) | State blob key | Owns |
|---|---|---|
| `AKS-SRE-Platform/terraform/aks-foundation` | `aks-foundation.terraform.tfstate` | RG `rg-aks-platform-dev`, `aks-portfolio-dev`, temp `work` pool (gated), `data.azurerm_container_registry`, `azurerm_role_assignment.aks_acr_pull`, temp WI proof resources (gated by `enable_wi_proof = false`) |
| `FlashSale-Backend/infrastructure/terraform/release` | `release.terraform.tfstate` | RG `rg-flashsale-release`, ACR, GitHub release identity, 6 federated credentials, 2 role assignments |
| `FlashSale-Backend/infrastructure/terraform/backup-storage` | `backup-storage.terraform.tfstate` | RG `rg-flashsale-data-protection`, storage account, containers, management policy, operator role assignment |
| `Productionized-LegacyApp/infrastructure/terraform` | — | historical never-applied blueprint, **backend block commented out** |

⇒ Backing up only `aks-foundation.tfstate` (as the pasted plan does) would
**permanently lose the `release` and `backup-storage` state**. Three blobs must
be pulled and checksummed before the backend is deleted.

Role assignments prove the destroy order: three ACR-scoped assignments
(`AcrPush`/`AcrPull` for the release identity, `AcrPull` for the agentpool
identity) mean **the ACR must not be deleted before the two Terraform roots that
own those assignments are destroyed** — otherwise their `destroy` fails on a
missing resource.

Infrastructure is otherwise created by scripts, not Terraform: the state RG and
account come from `bootstrap-tfstate-backend.sh`, and the container immutability
policy is applied out-of-band (`bootstrap-immutability-policy.sh`) — i.e. it is
**not** in the `backup-storage` root's state and may need manual removal.

## 4. Blockers found during the read-only pass (all verified live)

1. **Storage firewall blocks the current operator IP.** Both accounts are
   `defaultAction: Deny` with a fixed allowlist; egress IP today is
   **not** on it (`az storage container list` / `az storage blob list` →
   *"blocked by network rules"*). Consequence: `terraform init`,
   `terraform state pull` and every blob inventory/download **fail 403 until the
   current IP is added** — this is the same failure recorded in
   `docs/evidence/phase7a/apply-2026-09-21-BLOCKED.md`.
2. **Phase C (backup preservation) is therefore BLOCKED, not PASS.** The local
   copies stop at `2026-09-20T15:36Z` (PostgreSQL `.dump` + RabbitMQ definitions);
   whether the account holds newer scheduled uploads **cannot be verified from
   this host**. The daily launchd job (`com.flashsale.offsite-backup`) is still
   loaded and its last exit status is non-zero, with empty logs since
   2026-09-21T02:30 — consistent with allowlist-induced upload failures.
   Deleting `rg-flashsale-data-protection` before this is verified would risk the
   only off-host copy.
3. **Undeclared resource group** `rg-apexinspect-demo` (§1) has no confirmed
   owner — the plan's own rule says STOP for UNKNOWN resources.
4. `.local/` is gitignored in this repo (`**/.local/`) but **not** in
   `FlashSale-Backend/.gitignore`; pulling state there without adding the ignore
   rule first risks committing a state file.

## 5. Corrected destroy order (replaces the plan's Phase D→H)

| # | Action | Root / tool | Gate |
|---|---|---|---|
| 0 | Add current operator IP to **both** storage firewalls (write op, needs explicit approval) | `az` | `terraform init` succeeds in all 3 roots |
| 1 | Classify `rg-apexinspect-demo` ownership | — | owner confirmed or left untouched |
| 2 | Add `/.local/` to `FlashSale-Backend/.gitignore` **before** any state pull | P01 | commit |
| 3 | `terraform state pull` for **3 roots** → gitignored local backups + SHA-256; never printed into chat/evidence | 3 roots | 3 checksums recorded |
| 4 | Blob inventory + download + checksum verification | P01 | preservation proven, else **BLOCKED** |
| 5 | `terraform plan -destroy` (saved) → apply for `aks-foundation` | P03 | `az aks show` NotFound, MC RG gone, no orphan disk/VMSS/LB/PIP |
| 6 | `terraform destroy` for `release` | P01 | ACR + identity + FICs gone |
| 7 | `terraform destroy` for `backup-storage` (remove immutability policy first if it blocks) | P01 | storage gone |
| 8 | Delete `rg-flashsale-tfstate` — **last**, only after 3 states are destroyed *and* backed up, and after confirming no other root uses it | `az` | backend gone |
| 9 | Final audit + `tasks/current.md` updates | — | zero unreviewed portfolio resources |

Deliberately **outside** the scope: `NetworkWatcherRG` (keep).

## 6. Claim discipline

No destruction has been performed and no Azure resource was created. When the
teardown is finally executed, the only defensible statement is: *"No known
billable portfolio Azure resources remain based on live Azure inventory."*
— never "the invoice will be $0", because billing data lags resource deletion.

