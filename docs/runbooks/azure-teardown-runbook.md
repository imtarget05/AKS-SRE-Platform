# Azure teardown runbook — `aks-portfolio-dev` (AKS-SRE-Platform)

**Status: PREPARED — NOT EXECUTED.**
No delete command in this document has been run. Every command in
[§1 Current state](#1-current-state-read-only-evidence) and
[§5 Evidence to capture before deleting](#5-evidence-to-capture-before-deleting)
is read-only and **has** been run on 2026-10-21; its output is committed under
`docs/evidence/azure/2026-10-21-prestop/`. Every command in
[§3 Destruction order](#3-destruction-order) and
[§7 Post-deletion verification](#7-post-deletion-verification) is **destructive
or verification-after-destructive and has NOT been run.**

> **Owner decision required before anything in §3 is executed.**
> See [§6 Questions for the owner](#6-questions-for-the-owner). The default
> posture is **keep the cluster running** until the owner answers.

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

**This cluster is billable.** It is a live `Succeeded` AKS cluster with one
`Ready` node and a running node pool. Leaving it in place continues to incur
Azure compute charges for the node pool and the managed control plane.

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

- [ ] Owner has answered [§6](#6-questions-for-the-owner) in writing.
- [ ] [§5 evidence](#5-evidence-to-capture-before-deleting) has been captured
      **and committed to git** (the 2026-10-21 snapshot is already committed at
      `docs/evidence/azure/2026-10-21-prestop/`; re-capture if anything changed).
- [ ] Local `terraform.tfstate` **and** `terraform.tfstate.backup` have been
      copied somewhere outside the repository (see [§4.2](#42-the-local-state-is-gitignored-and-unbacked)).
- [ ] `az login` context confirmed: `az account show` → the subscription in §0.
- [ ] A second person has read §3 and agrees the order is right.
- [ ] Someone is online for the whole window — `az aks delete` on a cluster
      with a node pool runs for **tens of minutes** and is not resumable from
      a laptop that sleeps.

---

## 3. Destruction order

**Two distinct steps, deliberately separated.** `az aks delete` removes the
cluster; `az group delete` removes the resource group and everything left in
it. Deleting the group alone would take the cluster with it, but it would also
take any other resource in the group without the chance to inspect the
intermediate state — and without the ability to keep the node pool's own
diagnostics. Deleting the cluster first leaves the group (and its state) in
place for a while, which is recoverable.

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
`docs/evidence/live-aks-2026-10-20/aks-live-evidence.md` still carries the
unqualified line `Status: AZURE_CLOUD_VERIFIED` and a `3 nodes Ready` claim
that its own committed `kubectl-nodes.txt` contradicts. The author of
`d628250` should confirm or correct it. If the cluster is deleted, the
"verified" claim must also say **"verified, then destroyed"** — as the
2026-10-20 file already does in one place but not in the other.

---

## 7. Post-deletion verification

Run only **after** §3 Step 2 has completed.

```bash
$ az aks list -o table
WARNING: The behavior of this command has been altered by the following extension: aks-preview
Name  Location  ResourceGroup  KubernetesVersion  CurrentKubernetesVersion  ProvisioningState  Fqdn
----  --------  -------------  ---------------  ------------------------  -------------------  ----
```
→ empty list.

```bash
$ az group list -o table
Name                      Location     Status
------------------------  -----------  ---------
NetworkWatcherRG          eastasia     Succeeded
rg-flashsale              southeastasia  Succeeded
```
→ `rg-aks-platform-dev` absent, and `MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` absent.

```bash
$ az aks show -g rg-aks-platform-dev -n aks-portfolio-dev -o table
(AzCLIResourceNotFound) Resource group 'rg-aks-platform-dev' could not be found
```
→ `NotFound`, which is the *expected* result and must not be read as a failure.

```bash
$ az resource list -g rg-aks-platform-dev -o table
(ResourceGroupNotFound) Resource group 'rg-aks-platform-dev' could not be found
```
→ zero resources.

```bash
$ kubectl --context aks-portfolio-dev get nodes
error: You must be logged in to the server (Unauthorized)
```
→ the context no longer authenticates; the cluster is gone.

---

## 8. Change log

| Date | Change |
| --- | --- |
| 2026-10-21 | Runbook authored. Read-only current-state capture executed and committed to `docs/evidence/azure/2026-10-21-prestop/`. **No delete command executed.** |
