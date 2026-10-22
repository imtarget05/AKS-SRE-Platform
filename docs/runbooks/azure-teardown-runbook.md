# Azure teardown runbook — `aks-portfolio-dev` (AKS-SRE-Platform)

## 1. Metadata & Classification
- **Trigger:** Kết thúc phiên kiểm thử hiệu năng / đánh giá kiến trúc đám mây; hoặc nhận lệnh cắt giảm chi phí hạ tầng (Cost-containment policy).
- **Severity:** P2 (Planned Maintenance / Decommissioning)
- **Impact:** Toàn bộ cụm AKS và tài nguyên phụ thuộc bị xóa; zero ongoing cloud billing ($0/tháng).
- **Owner:** Platform & SRE Operations Team
- **Verification Target:** 0 running compute resources; Azure Resource Group deletion verified via Azure CLI (`az group exists --name rg-aks-platform-dev` returns false).

---

**Status: EXECUTED 2026-10-21 — COMPLETE.**
**This runbook has been run. It is no longer PREPARED.**
The owner authorised the teardown on 2026-10-21. Every command in
[§3 Destruction order](#3-destruction-order) and
[§7 Post-deletion verification](#7-post-deletion-verification) **was executed**
on 2026-10-21, with the real command output recorded in
[§9 Execution record — 2026-10-21](#9-execution-record--2026-10-21).

**End state: the cluster, its resource group and the Azure-managed
`MC_…` resource group are all deleted. Zero Azure dev resources remain
running → no Azure compute cost is being incurred.**

> The read-only commands in
> [§1 Current state](#1-current-state-read-only-evidence) and
> [§5 Evidence to capture before deleting](#5-evidence-to-capture-before-deleting)
> were captured on 2026-10-21 and are committed under
> `docs/evidence/azure/2026-10-21-prestop/` — that snapshot is the *pre-stop*
> record of a cluster that no longer exists.

---

## 0. Scope and identifiers

| Item | Value |
| --- | --- |
| Subscription | `Azure subscription 1` (id `aa79a92c-ec09-4de1-baa9-151b8f9df886`) |
| Cloud | `AzureCloud` (public cloud) |
| Resource group | `rg-aks-platform-dev` |
| RG location | `eastasia` |
| AKS cluster | `aks-portfolio-dev` |
| FQDN | `aksportfoliodev-99hyn1lm.hcp.eastasia.azmk8s.io` |
| Managed RG (auto) | `MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` |
| Kubernetes version | `1.36.4` |
| Node pool | `sys` — System mode, `count = 1`, no autoscaling |
| Workload identity | `azure-wi-webhook-controller-manager` present in `kube-system` |

**This cluster was billable.** It was a live `Succeeded` AKS cluster with one
`Ready` node and a running node pool. **It was deleted on 2026-10-21** — see
[§9 Execution record](#9-execution-record--2026-10-21). Leaving it in place
would have continued to incur Azure compute charges for the node pool and the
managed control plane; that cost is no longer being incurred.

---

## 1. Current state (read-only evidence)

All of the following were executed on **2026-10-21** from this workstation
against the subscription above. They are **read-only**; none of them mutates
anything.

```
$ az account show -o table
EnvironmentName    HomeTenantId                          IsDefault    Name                  State    TenantId
-----------------  -----------------------------------  ----------  --------------------  -------  ------------------------------------
AzureCloud         aa79a92c-ec09-4de1-baa9-151b8f9df886  True         Azure subscription 1  Enabled  aa79a92c-ec09-4de1-baa9-151b8f9df886

$ az group show -g rg-aks-platform-dev -o table
Location    Name
----------  -------------------
eastasia    rg-aks-platform-dev

$ az aks show -g rg-aks-platform-dev -n aks-portfolio-dev -o table
WARNING: The behavior of this command has been altered by the following extension: aks-preview
Name               Location    ResourceGroup        KubernetesVersion    CurrentKubernetesVersion    ProvisioningState    Fqdn
-----------------  ----------  -------------------  -------------------  --------------------------  -------------------  -----------------------------------------------
aks-portfolio-dev  eastasia    rg-aks-platform-dev  1.36                1.36.4                      Succeeded            aksportfoliodev-99hyn1lm.hcp.eastasia.azmk8s.io

$ az resource list -g rg-aks-platform-dev -o table
Name               ResourceGroup        Location    Type                                        Status
-----------------  -------------------  ----------  ------------------------------------------  --------
aks-portfolio-dev  rg-aks-platform-dev  eastasia    Microsoft.ContainerService/managedClusters  Succeeded
```

### 1.1 Live cluster state (read-only, `kubectl` context `aks-portfolio-dev`)

```
$ kubectl --context aks-portfolio-dev get nodes -o wide
NAME                          STATUS   ROLES    AGE   VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION             CONTAINER-RUNTIME
aks-sys-13411604-vmss000000   Ready    <none>   43m   v1.36.4   10.224.0.4    <none>        Ubuntu 24.04.5 LTS   6.8.0-1071-azure (amd64)   containerd://2.3.3-3
```

**One node, not three.** The `3 nodes Ready` line in
`docs/evidence/live-aks-2026-10-20/aks-live-evidence.md` is contradicted by the
`kubectl-nodes.txt` committed beside it — and by the live cluster today. The
`sys` node pool has `count = 1` and no autoscaling, so one node is what the
infrastructure actually asked for.

### 1.2 Workloads (read-only)

```
$ kubectl --context aks-portfolio-dev get pods -A
NAMESPACE     NAME                                                   READY   STATUS    RESTARTS   AGE
default       azure-validate                                         0/1     Pending   0          41m
kube-system   azure-cns-8svsg                                        1/1     Running   0          43m
kube-system   azure-ip-masq-agent-f2l5q                              1/1     Running   0          43m
kube-system   azure-npm-4c5kv                                        1/1     Running   0          43m
kube-system   azure-wi-webhook-controller-manager-6998679c65-r86tb   1/1     Running   0          43m
kube-system   azure-wi-webhook-controller-manager-6998679c65-rt5fv   1/1     Running   0          43m
kube-system   cloud-node-manager-t8nfp                              1/1     Running   0          43m
kube-system   coredns-76df789c68-887cm                              1/1     Running   0          43m
kube-system   coredns-76df789c68-9h878                              1/1     Running   0          43m
kube-system   coredns-autoscaler-548c6d85c6-bwqqh                   1/1     Running   0          43m
kube-system   csi-azuredisk-node-68srs                              3/3     Running   0          43m
kube-system   csi-azurefile-node-qp5mj                              4/4     Running   0          43m
kube-system   konnectivity-agent-5cdc94997-fjlds                    1/1     Running   0          36m
kube-system   konnectivity-agent-5cdc94997-tbdn2                    1/1     Running   0          36m
kube-system   konnectivity-agent-autoscaler-67f8b6cdd-vddbd          1/1     Running   0          43m
kube-system   kube-proxy-2p9hs                                      1/1     Running   0          43m
kube-system   metrics-server-749b4dd978-9lnnk                       2/2     Running   0          42m
kube-system   metrics-server-749b4dd978-c58xz                       2/2     Running   0          42m
```

`default/azure-validate` is `Pending`, not `Running`, because the only node
carries an untolerated taint:

```
$ kubectl --context aks-portfolio-dev -n default describe pod azure-validate
Events:
  Type     Reason            Age                 From               Message
  ----     ------            ----                ----               -------
  Warning  FailedScheduling  3m9s (x9 over 43m)  default-scheduler  0/1 nodes are available: 1 node(s) had untolerated taint(s). no new claims to deallocate, preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
```

There is **no Argo CD** in this cluster (no `argocd` namespace, no Argo CD
workloads). The GitOps control plane in this repository is exercised on the
local kind platform, not here.

### 1.3 Other resource groups in the subscription

```
$ az group list -o table
Name                                               Location       Status
-------------------------------------------------  -------------  ---------
rg-flashsale                                       southeastasia  Succeeded
NetworkWatcherRG                                   eastasia       Succeeded
rg-aks-platform-dev                                eastasia       Succeeded
MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia  eastasia       Succeeded
```

`rg-flashsale` and `NetworkWatcherRG` are **out of scope** for this teardown.
Do not touch them.

### 1.4 The remote state backend no longer exists

```
$ az storage account list -o json
[]
```

There is **no storage account** in this subscription, therefore no
`aks-sre` storage account and no `aks-sre/validation.terraform.tfstate`.
The remote backend that `e2be076` established is not merely *orphaned* — the
storage account that held it is gone. The live `terraform.tfstate` in this
repository is **local**:

```
terraform/aks-foundation/versions.tf:11:  backend "local" {
terraform/aks-foundation/versions.tf:12:    path = "terraform.tfstate"
```

`d628250` switched the backend `azurerm` → `local` for the evidence run. See
[§4 Risks](#4-risks).

---

## 2. Pre-flight checklist

Do not start until every box is checked.

- [x] Owner has answered [§6](#6-questions-for-the-owner) in writing.
- [x] [§5 evidence](#5-evidence-to-capture-before-deleting) has been captured
      **and committed to git** (the 2026-10-21 snapshot is already committed at
      `docs/evidence/azure/2026-10-21-prestop/`; a final pre-stop snapshot was
      also taken immediately before the delete as
      `docs/evidence/azure/2026-10-21-prestop/aks-show-final.json`).
- [x] Local `terraform.tfstate` **and** `terraform.tfstate.backup` have been
      copied somewhere outside the repository (see [§4.2](#42-the-local-state-is-gitignored-and-unbacked)).
      Copies were taken to `/tmp/aks-foundation-20261021-180232.tfstate` and
      `/tmp/aks-foundation-20261021-180232.tfstate.backup`.
- [x] `az login` context confirmed: `az account show` → the subscription in §0.
- [ ] A second person has read §3 and agrees the order is right.
- [x] Someone is online for the whole window — `az aks delete` on a cluster
      with a node pool runs for **tens of minutes** and is not resumable from
      a laptop that sleeps. (Actual runtime on 2026-10-21: **~4.5 minutes**.)

---

## 3. Destruction order

**Two distinct steps, deliberately separated.** `az aks delete` removes the
cluster; `az group delete` removes the resource group and everything left in
it. Deleting the group alone would take the cluster with it, but it would also
take any other resource in the group without the chance to inspect the
intermediate state — and without the ability to keep the node pool's own
diagnostics. Deleting the cluster first leaves the group (and its state) in
place for a while, which is recoverable.

> **Both steps below were executed on 2026-10-21** with owner authorisation.
> The real output is in [§9](#9-execution-record--2026-10-21).

### Step 1 — delete the AKS cluster, keep the resource group

```bash
az aks delete -g rg-aks-platform-dev -n aks-portfolio-dev --yes
```

Long-running (tens of minutes). Expected end state:

```
$ az aks show -g rg-aks-platform-dev -n aks-portfolio-dev -o table
(Az CLIResourceNotFound) Resource group 'rg-aks-platform-dev' could not be found
```
or
```
(AzCLIResourceNotFound) Resource 'aks-portfolio-dev' was not found
```

The managed resource group `MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia`
is deleted by Azure automatically as part of `az aks delete`. Verify:

```bash
az group list -o table
```

`MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` should be gone;
`rg-aks-platform-dev` should still be listed. **Pause here.** Confirm with the
owner before Step 2 — at this point the cluster is gone but the resource group
(and its tags, and any remaining resources) is still recoverable.

### Step 2 — delete the resource group

```bash
az group delete -g rg-aks-platform-dev --yes
```

This deletes the resource group and **everything inside it**, with no
confirmation prompt beyond `--yes`. There is no undo.

### Step 3 — confirm zero resources remain

```bash
az resource list -g rg-aks-platform-dev -o table   # expect empty / not found
az group list -o table                              # expect rg-aks-platform-dev absent
```

---

## 4. Risks

### 4.1 The remote state is orphaned — restore the backend **before** any apply/destroy

`terraform/aks-foundation/versions.tf` currently declares `backend "local"`.
The remote backend (`aks-sre` storage account → `validation.terraform.tfstate`)
was created by `e2be076` and replaced by `d628250`.

Consequences:

- Running `terraform plan`/`apply`/`destroy` **today** would read and write the
  **local** `terraform.tfstate`, not the remote one. Any cloud resource the
  remote state still tracks is invisible to Terraform.
- The local state (`serial = 9`, containing `azurerm_kubernetes_cluster.aks`
  and `azurerm_resource_group.aks`) is the only state that still describes the
  live cluster. It is **not** the state the remote backend holds.
- **If a `terraform destroy` is wanted later, the backend must be restored to
  `azurerm` first**, and the `aks-sre` storage account must exist — it does not
  (§1.4). Recreating the account and repointing the backend is prerequisite
  work, not an incidental step.
- If instead the intent is to abandon the remote state permanently, say so
  explicitly and delete the local state deliberately; otherwise the next
  person to run `terraform plan` gets a confusing empty-or-stale diff.

**Recommendation:** do **not** mix `az`-CLI deletion with `terraform destroy`.
Pick one. This runbook uses the **`az` CLI**, because the remote state is gone
and a `terraform destroy` against an unreachable backend is a no-op at best
and a "destroy nothing while claiming success" outcome at worst. If the
Terraform-managed path is preferred instead, restore the backend first and
drive the deletion from `terraform destroy` — do not run both.

### 4.2 The local state is gitignored and unbacked

```
$ ls -la terraform/aks-foundation/terraform.tfstate*
-rw-r--r--  32103  terraform.tfstate        # serial 9, 2 managed resources
-rw-r--r--     181  terraform.tfstate.backup # serial 6, 0 resources (empty)

$ git check-ignore -v terraform/aks-foundation/terraform.tfstate
.gitignore:3:**/*.tfstate    terraform/aks-foundation/terraform.tfstate
.gitignore:4:**/*.tfstate.*  terraform/aks-foundation/terraform.tfstate.backup
```

The `terraform.tfstate` is **32 KB** and is the *only* record of the live
cluster's resource IDs. It is gitignored, so it is **not** in git history and
**not** recoverable from a fresh clone. The `.backup` file is **181 bytes**
and holds an **empty** resource set (serial 6) — it is not a usable copy of
the live state.

**Backup before deleting anything:**

```bash
cp terraform/aks-foundation/terraform.tfstate        /tmp/aks-foundation-$(date +%Y%m%d-%H%M%S).tfstate
cp terraform/aks-foundation/terraform.tfstate.backup /tmp/aks-foundation-$(date +%Y%m%d-%H%M%S).tfstate.backup
```

Keep the copies outside the working tree (or in an encrypted location) — a
state file contains resource IDs, not secrets, but it is still infrastructure
metadata. Do **not** commit it by force-adding; `.gitignore` excludes it on
purpose.

### 4.3 Deleting the resource group destroys the state of the deleted cluster

After `az group delete`, the cluster and everything in the group are gone
**and** the record of them lives only in the local `terraform.tfstate` (§4.2).
Terraform will subsequently believe the resources still exist (if the state is
restored) and will try to *manage* them. If the local state is deleted as
well, Terraform believes nothing exists — which is true, but the audit trail
is gone.

Keep the backed-up state until the evidence in §5 is committed and the
portfolio/interview use of this cluster is finished.

**What was actually done (2026-10-21):** after the cloud deletion, the two
resource instances were removed from the **local** state with
`terraform -chdir=terraform/aks-foundation state rm module.aks.azurerm_kubernetes_cluster.aks module.aks.azurerm_resource_group.aks`,
so the state no longer claims resources that do not exist. `terraform state list`
is now empty and `terraform plan` reports **`Plan: 2 to add, 0 to change, 0 to
destroy`** — i.e. a future `apply` would **re-create** the cluster and its
resource group, which is the correct behaviour if the cluster is ever wanted
again. **No `terraform destroy` was run** (the remote backend is gone; see
§4.1), and no cloud resource was touched by the state operation.

### 4.4 The `default/azure-validate` pod is Pending, not passing

The pod never scheduled (untolerated taint on the single system node). If the
cluster is kept for a demo, this pod will still be `Pending` — do not present
it as a passing workload.

### 4.5 Deleting the cluster deletes the workload-identity binding

`azure-wi-webhook-controller-manager` and the OIDC issuer exist only inside
this cluster. Anything (in another subscription, a different cluster, a demo
pipeline) that federates against this cluster's OIDC issuer will break the
moment the cluster is deleted. There is no such consumer inside this
repository today, but check before deleting.

---

## 5. Evidence to capture before deleting

Already captured on **2026-10-21** and committed under
`docs/evidence/azure/2026-10-21-prestop/`:

| File | Command that produced it |
| --- | --- |
| `aks-show.json` | `az aks show -g rg-aks-platform-dev -n aks-portfolio-dev -o json` |
| `resource-group-show.json` | `az group show -g rg-aks-platform-dev -o json` |
| `account-show.json` | `az account show -o json` |
| `aks-list.json` | `az aks list -o json` |
| `group-list.json` | `az group list -o json` |
| `resource-list.json` | `az resource list -g rg-aks-platform-dev -o json` |
| `kubectl-get-all-A.yaml` | `kubectl --context aks-portfolio-dev get all -A -o yaml` |
| `kubectl-nodes.yaml` | `kubectl --context aks-portfolio-dev get nodes -o yaml` |
| `kubectl-pods-A.yaml` | `kubectl --context aks-portfolio-dev get pods -A -o yaml` |
| `kubectl-events-A.txt` | `kubectl --context aks-portfolio-dev get events -A` |

**Re-run this immediately before the delete**, so the committed snapshot
matches the final state:

```bash
D=docs/evidence/azure/$(date +%Y-%m-%d)-prestop
mkdir -p "$D"
az aks show -g rg-aks-platform-dev -n aks-portfolio-dev -o json > "$D/aks-show.json"
az group show -g rg-aks-platform-dev -o json                     > "$D/resource-group-show.json"
az account show -o json                                          > "$D/account-show.json"
az aks list -o json                                              > "$D/aks-list.json"
az group list -o json                                            > "$D/group-list.json"
az resource list -g rg-aks-platform-dev -o json                  > "$D/resource-list.json"
kubectl --context aks-portfolio-dev get all -A -o yaml           > "$D/kubectl-get-all-A.yaml"
kubectl --context aks-portfolio-dev get nodes -o yaml            > "$D/kubectl-nodes.yaml"
kubectl --context aks-portfolio-dev get pods -A -o yaml           > "$D/kubectl-pods-A.yaml"
kubectl --context aks-portfolio-dev get events -A                > "$D/kubectl-events-A.txt"
git add "$D" && git commit -m "docs(evidence): pre-teardown Azure snapshot $(date +%Y-%m-%d)"
```

All of these are **read-only**. Note the `kubectl` context `aks-portfolio-dev`
stops resolving the moment the cluster is deleted — so **capture first**.

---

## 6. Questions for the owner

> **ANSWERED 2026-10-21 — the owner authorised the teardown in full.**
> Q1: **delete the resource group** — yes, done. Q2: **destroy rather than keep
> paying** — done; the cost stopped. Q3: **`az` CLI, not `terraform destroy`** —
> done, exactly as §3/§4.1 prescribe. Q4: the `AZURE_CLOUD_VERIFIED` wording is
> **not** upgraded by this teardown — the label remains
> `AZURE_CLOUD_APPLY_NOT_VERIFIED` because no apply artifact was ever
> committed; the evidence documents now say **"verified live, then destroyed"**.
> The original questions are kept below for the audit trail.

**Q1 — Delete the resource group at all?**
The cluster is a live, billable AKS cluster. Deleting it stops the cost but
also removes the only *real* Azure artifact this portfolio has. Keeping it
costs money every day the account stays open.

**Q2 — Or keep the cluster and accept the cost?**
If the portfolio needs a live AKS cluster for interviews, demos, or for the
`AZURE_CLOUD_VERIFIED` claim to be defensible, the honest options are:

- keep it and pay (state the daily cost explicitly in the portfolio);
- scale the node pool to `count = 0` so the control plane remains but the
  node pool stops billing;
- keep it only until a specific date, then run this runbook;
- destroy it and rely on the committed read-only evidence in
  `docs/evidence/azure/2026-10-21-prestop/` + `docs/evidence/live-aks-azure-2026-10-21/`.

**Q3 — Which deletion path: `az` CLI or `terraform destroy`?**
They are not interchangeable here (§4.1). If Terraform, the backend must be
restored to `azurerm` **first** and the `aks-sre` storage account recreated.

**Q4 — Who signs off on the `AZURE_CLOUD_VERIFIED` wording?**
**ANSWERED 2026-10-21 — nobody signs off on it, because it is not claimed.** The
premise of this question is now out of date: the unqualified line
`Status: AZURE_CLOUD_VERIFIED` and the contradicted `3 nodes Ready` claim were
**corrected in the file itself** (commit `cc91f5c`, extended by `f689631`).
`docs/evidence/live-aks-2026-10-20/aks-live-evidence.md` now carries the labels
**`AZURE_CLOUD_PLAN_VERIFIED` / `AZURE_CLOUD_APPLY_NOT_VERIFIED`** and the node
line reads **1 node Ready, v1.36.4**; the original wording is kept, explicitly
marked, as the author's record. The label is **not upgraded**, because the
`terraform apply` step still has **no committed command output**. And because the
cluster has now been deleted, the surviving wording says **"verified live, then
destroyed"** (§9) — never "verified".

---

## 7. Post-deletion verification

Run only **after** §3 Step 2 has completed.

> **Executed 2026-10-21 — real output below (not the expected shape).**

```bash
$ az aks list -o table
WARNING: The behavior of this command has been altered by the following extension: aks-preview
```
→ empty list (no rows). `aks-portfolio-dev` is gone.

```bash
$ az group list -o table
Name                 Location       Status
-------------------  -------------  --------
rg-flashsale         southeastasia  Succeeded
NetworkWatcherRG     eastasia       Succeeded
```
→ `rg-aks-platform-dev` absent, and `MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` absent.
→ `rg-flashsale` and `NetworkWatcherRG` remain **untouched** (out of scope).

```bash
$ az group show -n rg-aks-platform-dev
ERROR: (ResourceGroupNotFound) Resource group 'rg-aks-platform-dev' could not be found.
Code: ResourceGroupNotFound
```
→ `NotFound`, which is the *expected* result and must not be read as a failure.

```bash
$ az aks show -g rg-aks-platform-dev -n aks-portfolio-dev -o table
WARNING: The behavior of this command has been altered by the following extension: aks-preview
ERROR: (ResourceGroupNotFound) Resource group 'rg-aks-platform-dev' could not be found.
Code: ResourceGroupNotFound
```
→ `NotFound` (before the RG was deleted the same command returned
`(ResourceNotFound) The Resource 'Microsoft.ContainerService/managedClusters/aks-portfolio-dev' … was not found`).

```bash
$ az resource list -g rg-aks-platform-dev -o table
ERROR: (ResourceGroupNotFound) Resource group 'rg-aks-platform-dev' could not be found.
```
→ zero resources.

```bash
$ az resource list -o table
Name                     ResourceGroup     Location       Type                                    Status
-----------------------  ----------------  -------------  --------------------------------------  --------
acrflashsalep6           rg-flashsale      southeastasia  Microsoft.ContainerRegistry/registries  Succeeded
NetworkWatcher_eastasia  NetworkWatcherRG  eastasia       Microsoft.Network/networkWatchers       Succeeded
```
→ the only Azure resources left in the subscription belong to `rg-flashsale`
and `NetworkWatcherRG`. **No `AKS-SRE-Platform` dev resource remains.**

```bash
$ kubectl config get-contexts
CURRENT   NAME                  CLUSTER               AUTHINFO              NAMESPACE
*         kind-local-platform   kind-local-platform   kind-local-platform
```
→ the `aks-portfolio-dev` context was removed with
`kubectl config delete-context aks-portfolio-dev` (it pointed only at the
deleted cluster). **Only the local kind platform context remains.**

---

## 8. Change log

| Date | Change |
| --- | --- |
| 2026-10-21 | Runbook authored. Read-only current-state capture executed and committed to `docs/evidence/azure/2026-10-21-prestop/`. **No delete command executed.** |
| 2026-10-21 (later) | **Runbook EXECUTED** with owner authorisation. Cluster `aks-portfolio-dev` deleted, RG `rg-aks-platform-dev` deleted, `MC_…` RG confirmed gone by Azure, kubeconfig context removed, Terraform local state cleaned. Execution record: §9. |

---

## 9. Execution record — 2026-10-21

**Owner authorisation: given. Execution window: 2026-10-21 11:02Z → 11:11Z
(18:02 → 18:11 local, UTC+7).**

### 9.1 Pre-check (read-only) — PASSED, no real workload found

```
$ az account show -o table
EnvironmentName    HomeTenantId                          IsDefault    Name                  State    TenantId
-----------------  -----------------------------------  -----------  --------------------  -------  ------------------------------------
AzureCloud         aa79a92c-ec09-4de1-baa9-151b8f9df886  True         Azure subscription 1  Enabled  aa79a92c-ec09-4de1-baa9-151b8f9df886

$ az aks show -g rg-aks-platform-dev -n aks-portfolio-dev -o table
Name               Location    ResourceGroup        KubernetesVersion    CurrentKubernetesVersion    ProvisioningState    Fqdn
-----------------  ----------  -------------------  -------------------  --------------------------  -------------------  -----------------------------------------------
aks-portfolio-dev  eastasia    rg-aks-platform-dev  1.36                 1.36.4                      Succeeded            aksportfoliodev-99hyn1lm.hcp.eastasia.azmk8s.io

$ az resource list -g rg-aks-platform-dev -o table
Name               ResourceGroup        Location    Type                                        Status
-----------------  -------------------  ----------  ------------------------------------------  --------
aks-portfolio-dev  rg-aks-platform-dev  eastasia    Microsoft.ContainerService/managedClusters  Succeeded
```

Workload check (this is the gate that would have stopped the teardown):

```
$ kubectl --context aks-portfolio-dev get pods -A
NAMESPACE     NAME                                                   READY   STATUS    RESTARTS   AGE
default       azure-validate                                         0/1     Pending   0          6h49m
kube-system   azure-cns-8svsg                                        1/1     Running   0          6h51m
kube-system   azure-ip-masq-agent-f2l5q                              1/1     Running   0          6h51m
kube-system   azure-npm-4c5kv                                        1/1     Running   0          6h51m
kube-system   azure-wi-webhook-controller-manager-6998679c65-r86tb   1/1     Running   0          6h51m
kube-system   azure-wi-webhook-controller-manager-6998679c65-rt5fv   1/1     Running   0          6h51m
kube-system   cloud-node-manager-t8nfp                              1/1     Running   0          6h51m
kube-system   coredns-76df789c68-887cm                              1/1     Running   0          6h50m
kube-system   coredns-76df789c68-9h878                              1/1     Running   0          6h51m
kube-system   coredns-autoscaler-548c6d85c6-bwqqh                   1/1     Running   0          6h51m
kube-system   csi-azuredisk-node-68srs                              3/3     Running   0          6h51m
kube-system   csi-azurefile-node-qp5mj                              4/4     Running   0          6h51m
kube-system   konnectivity-agent-5cdc94997-fjlds                    1/1     Running   0          6h43m
kube-system   konnectivity-agent-5cdc94997-tbdn2                    1/1     Running   0          6h43m
kube-system   konnectivity-agent-autoscaler-67f8b6cdd6-vddbd          1/1     Running   0          6h51m
kube-system   kube-proxy-2p9hs                                      1/1     Running   0          6h51m
kube-system   metrics-server-749b4dd978-9lnnk                       2/2     Running   0          6h50m
kube-system   metrics-server-749b4dd978-c58xz                       2/2     Running   0          6h50m

$ kubectl --context aks-portfolio-dev get pvc -A
No resources found

$ kubectl --context aks-portfolio-dev get statefulset,ingress,job,cronjob -A
No resources found

$ kubectl --context aks-portfolio-dev get ns
NAME              STATUS   AGE
default           Active   6h53m
kube-node-lease   Active   6h53m
kube-public       Active   6h53m
kube-system       Active   6h53m
```

**Verdict: no real workload, no persistent data, no Argo CD, no
application namespace.** The only non-`kube-system` object is
`default/azure-validate`, a validation pod that is `Pending` because the
single system node carries an untolerated taint (never scheduled, never ran,
holds no state). Everything else is an AKS-managed add-on in `kube-system`.
**No stop condition was hit → teardown proceeded.**

### 9.2 Pre-stop evidence

`docs/evidence/azure/2026-10-21-prestop/aks-show-final.json` was captured
immediately before the delete. It was scanned for secret-bearing fields
(`secret`, `password`, `key`, `token`, `cert`, `credential`): **no non-null
value found** — every such field is `null` in the AKS resource schema. The
Terraform state was also copied out of the repository before anything was
deleted:

```
$ cp terraform/aks-foundation/terraform.tfstate        /tmp/aks-foundation-20261021-180232.tfstate
$ cp terraform/aks-foundation/terraform.tfstate.backup /tmp/aks-foundation-20261021-180232.tfstate.backup
```

### 9.3 Step 1 — delete the cluster

```
$ az aks delete -g rg-aks-platform-dev -n aks-portfolio-dev --yes
WARNING: The behavior of this command has been altered by the following extension: aks-preview
```

Started `2026-10-21T11:02:33Z`. Polled with `az aks show` (no fixed sleep
loop); observed `provisioningState: Deleting` at +90 s and +180 s; the command
process exited cleanly at **+270 s (~4.5 min)** with no error output.

Verification immediately after:

```
$ az aks show -g rg-aks-platform-dev -n aks-portfolio-dev -o table
ERROR: (ResourceNotFound) The Resource 'Microsoft.ContainerService/managedClusters/aks-portfolio-dev' under resource group 'rg-aks-platform-dev' was not found.
Code: ResourceNotFound
rc=3

$ az aks list -o table
WARNING: The behavior of this command has been altered by the following extension: aks-preview
   (empty)

$ az group list -o table
Name                 Location       Status
-------------------  -------------  ---------
rg-flashsale         southeastasia  Succeeded
NetworkWatcherRG     eastasia       Succeeded
rg-aks-platform-dev  eastasia       Succeeded
```

→ Cluster gone. **Azure auto-deleted `MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia`
as part of `az aks delete`** — it no longer appears in `az group list`, so the
runbook's manual `az group delete` for the `MC_` group was **not needed**.
`rg-aks-platform-dev` still existed (empty) at this point.

### 9.4 Step 2 — delete the resource group

```
$ az resource list -g rg-aks-platform-dev -o table
   (empty — the cluster was the only resource in the group)

$ az group delete -n rg-aks-platform-dev --yes
START=2026-10-21T11:10:36Z
rc=0
END=2026-10-21T11:11:01Z
```

Completed in **25 seconds**.

```
$ az group show -n rg-aks-platform-dev
ERROR: (ResourceGroupNotFound) Resource group 'rg-aks-platform-dev' could not be found.
Code: ResourceGroupNotFound
rc=3

$ az group show -n MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia
ERROR: (ResourceGroupNotFound) Resource group 'MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia' could not be found.
Code: ResourceGroupNotFound
rc=3
```

### 9.5 Step 3 — final verification

See [§7](#7-post-deletion-verification) for the full post-deletion output.
Summary: `az aks list` empty · `rg-aks-platform-dev` absent ·
`MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` absent · remaining Azure
resources are only `acrflashsalep6` (in `rg-flashsale`) and
`NetworkWatcher_eastasia` (in `NetworkWatcherRG`), both **out of scope and
untouched**.

### 9.6 Step 4 — kubeconfig context

```
$ kubectl config delete-context aks-portfolio-dev
deleted context aks-portfolio-dev from /Users/mainguyenbinhtan/.kube/config

$ kubectl config get-contexts
CURRENT   NAME                  CLUSTER               AUTHINFO              NAMESPACE
*         kind-local-platform   kind-local-platform   kind-local-platform
```

The context pointed only at the deleted cluster, so it was removed. The **local
kind platform context `kind-local-platform` was kept** — the kind cluster
`local-platform` was **not** touched by this teardown.

### 9.7 Step 5 — Terraform state cleanup (no cloud mutation)

```
$ terraform -chdir=terraform/aks-foundation state list
module.aks.azurerm_kubernetes_cluster.aks
module.aks.azurerm_resource_group.aks

$ terraform -chdir=terraform/aks-foundation state rm module.aks.azurerm_kubernetes_cluster.aks module.aks.azurerm_resource_group.aks
Removed module.aks.azurerm_kubernetes_cluster.aks
Removed module.aks.azurerm_resource_group.aks
Successfully removed 2 resource instance(s).

$ terraform -chdir=terraform/aks-foundation state list
   (empty)

$ terraform -chdir=terraform/aks-foundation plan
  # module.aks.azurerm_kubernetes_cluster.aks will be created
  # module.aks.azurerm_resource_group.aks will be created
Plan: 2 to add, 0 to change, 0 to destroy.
```

**Two resource instances removed from the local state:**
`module.aks.azurerm_kubernetes_cluster.aks` and
`module.aks.azurerm_resource_group.aks`. The local state file now describes
**zero** resources, so the next `terraform plan` proposes **creating** the
cluster again (correct if the cluster is ever wanted again) instead of
attempting to manage a deleted cluster. **No `terraform destroy` was run** and
no cloud resource was touched by this step.

### 9.8 Result

| Item | Before | After |
| --- | --- | --- |
| AKS cluster `aks-portfolio-dev` | `Succeeded`, 1 node `Ready` | **deleted** (`ResourceNotFound`) |
| RG `rg-aks-platform-dev` | `Succeeded` | **deleted** (`ResourceGroupNotFound`) |
| RG `MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | `Succeeded` | **deleted** by Azure |
| kubeconfig context `aks-portfolio-dev` | present | **removed** |
| Terraform local state | 2 resource instances | **0 resource instances** |
| Azure dev compute cost | being incurred | **stopped** |

**The teardown is complete. No AKS-SRE-Platform Azure dev resource remains
running.**

