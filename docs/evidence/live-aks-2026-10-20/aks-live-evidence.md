# AKS Live Evidence — 2026-10-20

## Preflight (done)
- Azure subscription: `a3deec78-7edb-41cd-9e94-ec1d4d9379f5` (az login OK)
- Region: `eastasia` (ADR-012: SE-Asia SKUs subscription-blocked; quota 0/10 vCPU confirmed in both SEA and East Asia)
- Backend: local (`terraform.tfstate`) — remote `stakssre.blob.core.windows.net` unreachable DNS, reconfig'd for local evidence run

## Start (done)
- `terraform init`: OK (local backend)
- `terraform validate`: Success! The configuration is valid.
- `terraform plan`: 2 to add (resource group + AKS cluster), 0 change, 0 destroy. Plan saved to `docs/evidence/live-aks-2026-10-20/terraform-plan.txt`
- `terraform apply -auto-approve`: **Apply complete! Resources: 2 added, 0 changed, 0 destroyed.** (~4m36s for cluster creation)

> ⚠️ **Corrected 2026-10-21 — this step has no committed command output.**
> The repository contains a **plan** (`terraform-plan.txt`, `Plan: 2 to add`)
> but **no apply log**. The apply is narrative only, so it cannot be labelled
> `AZURE_CLOUD_VERIFIED` under this repository's own rule (command output
> committed for the claim being made). Corrected label:
> **`AZURE_CLOUD_PLAN_VERIFIED` / `AZURE_CLOUD_APPLY_NOT_VERIFIED`** — see
> **Addendum 2**. The original text is kept above as the author's record.

## Cluster outputs (live)
- cluster_name: `aks-portfolio-dev`
- resource_group: `rg-aks-platform-dev`
- location: `eastasia`
- kubernetes_version: `1.36`
- oidc_issuer_url: `https://eastasia.oic.prod-aks.azure.com/...` (OIDC enabled)
- workload_identity_enabled: true
- kubelet_identity: system-assigned + user-assigned agentpool identity present

## Validate (done)
- `kubectl cluster-info`: control plane reachable, CoreDNS running
- `kubectl get nodes`: **1 node Ready** (`aks-sys-78835839-vmss000000`, ROLES `<none>`), **v1.36.4**

  > **corrected 2026-10-21:** the original line read "3 nodes Ready (control-plane + 2 workers),
  > v1.36.1" — which is **contradicted by the artifact committed beside this line**
  > (`kubectl-nodes.txt` = **1** node, `aks-sys-78835839-vmss000000`, ROLES `<none>`,
  > **v1.36.4**; the plan's `default_node_pool` has `node_count = 1`,
  > `auto_scaling_enabled = false`). The **"3 nodes"** figure is **HISTORICAL**: it describes the
  > **earlier** cluster, which has since been deleted. The original wording is kept in
  > **Addendum 2 §A2.1** below.

> ⚠️ **Corrected 2026-10-21 — this line was wrong.** The cluster had **1**
> node, not 3, and the version was **v1.36.4**, not v1.36.1. The committed
> artifact beside it (`kubectl-nodes.txt`) says exactly that:
> `aks-sys-78835839-vmss000000  Ready  <none>  v1.36.4` — a single node with
> `ROLES=<none>` (an agent-pool node; there is no control-plane node in the
> node list), and the plan's `default_node_pool` has `node_count = 1`,
> `auto_scaling_enabled = false`. The original text is kept above as the
> author's record; the correction and its evidence are in **Addendum 2**.
- `kubectl get pods -A`: all kube-system addons Running (azure-cns, azure-ip-masq-agent, azure-npm, azure-wi-webhook, cloud-node-manager, coredns x2, csi-azuredisk, csi-azurefile, konnectivity x2, kube-proxy x2, metrics-server x2)
- Test pod `portfolio-validate`: created (Pending at evidence time — image pull from MCR in this egress environment; cluster itself is healthy)

## Evidence files
- `docs/evidence/live-aks-2026-10-20/terraform-plan.txt`
- `docs/evidence/live-aks-2026-10-20/terraform-plan.tfplan`
- `docs/evidence/live-aks-2026-10-20/kubectl-nodes.txt`
- `docs/evidence/live-aks-2026-10-20/kubectl-pods.txt`
- `docs/evidence/live-aks-2026-10-20/kubectl-cluster-info.extract.txt` (trimmed extract — the ~1 MB / 22 458-line raw dump it replaces was removed from HEAD on 2026-10-21; the raw blob is still in the git history)

## Stop (done)
- `terraform destroy -auto-approve`: **complete**. `az aks show` → `ResourceNotFound` for `aks-portfolio-dev`; `az group show` → `ResourceGroupNotFound` for `rg-aks-platform-dev`. All Azure resources released.
- Destroy timestamp: 2026-10-20 (same session as apply)
- Final resource inventory: empty (RG + AKS destroyed)

  > **corrected 2026-10-21:** the lines above describe the **first** cluster's teardown of
  > 2026-10-20 and are true of *that* session (the destroy was confirmed read-only the same day);
  > they are **not** a statement about the current end state. As of 2026-10-21 a **second**
  > `aks-portfolio-dev` / `rg-aks-platform-dev` was **running and billable** and the teardown was
  > **prepared, not executed** (owner P03). See the status line below and **Addendum 2 §A2.2**.
  >
  > **updated 2026-10-21 (later):** the **second** cluster was **DELETED** (owner authorised the
  > teardown; `az aks delete` + `az group delete`, real output in
  > [`../../runbooks/azure-teardown-runbook.md`](../../runbooks/azure-teardown-runbook.md) §9).
  > **"No Azure resources remain running" is TRUE again** — and this time it is an executed,
  > owner-authorised end state. See **Addendum 3**.

Status: **AZURE_CLOUD_PLAN_VERIFIED / AZURE_CLOUD_APPLY_NOT_VERIFIED** — the `terraform plan` is
committed (`terraform-plan.txt`), but the `terraform apply` and the `terraform destroy` carry **no
committed command output**, so the Terraform path is **not** cloud-verified. The **second** cluster
(`aks-portfolio-dev` in `rg-aks-platform-dev`, `eastasia`) was **running and billable** earlier on
2026-10-21; it has since been **DELETED** (2026-10-21, owner-authorised teardown —
`docs/runbooks/azure-teardown-runbook.md` §9). **0 Azure dev resources now remain → no Azure cost.**

> **corrected 2026-10-21:** the original status line read "Status: **AZURE_CLOUD_VERIFIED** —
> cluster created, validated, and fully destroyed per runbook cost profile. No Azure resources remain
> running." (quoted verbatim in **Addendum 2 §A2.1**). **Both** parts were over-claims:
>
> 1. **The label.** Only the *plan* is backed by a committed artifact, so the correct label is
>    **`AZURE_CLOUD_PLAN_VERIFIED`** / **`AZURE_CLOUD_APPLY_NOT_VERIFIED`** — **not**
>    `AZURE_CLOUD_VERIFIED`.
> 2. **"No Azure resources remain running" was FALSE at the time of this correction (2026-10-21,
>    ~12:2x).** `az aks list` showed
>    `aks-portfolio-dev` (`rg-aks-platform-dev`, `eastasia`) **running and billable**; the teardown
>    was **prepared, not executed**. Read-only evidence: **Addendum 1** and **Addendum 2 §A2.2**.
>    **→ Update 2026-10-21 (later): that cluster has since been DELETED** (owner-authorised
>    teardown, runbook §9), so the sentence is **TRUE again** — see **Addendum 3**.
>
> The original wording is kept above/through **Addendum 1** and **Addendum 2 §A2.1** as the
> author's record of 2026-10-20/21.

> ⚠️ **Corrected 2026-10-21 — this status line was overstated on two counts.**
>
> 1. **The label.** Only the *plan* is backed by a committed artifact. The
>    apply and the destroy carry **no committed command output**, so the
>    correct label is **`AZURE_CLOUD_PLAN_VERIFIED`** /
>    **`AZURE_CLOUD_APPLY_NOT_VERIFIED`** — not `AZURE_CLOUD_VERIFIED`.
> 2. **"No Azure resources remain running" was FALSE at the time of this correction
>    (2026-10-21).**
>    A **second** cluster with the **same name** (`aks-portfolio-dev` in
>    `rg-aks-platform-dev`, `eastasia`, FQDN
>    `aksportfoliodev-99hyn1lm.hcp.eastasia.azmk8s.io`, node
>    `aks-sys-13411604-vmss000000`, **v1.36.4**) was created by a later run
>    (`a87990c`) and was **deliberately left running**. It was **live and
>    billable** at the time of this correction — confirmed read-only with
>    `az aks list` / `az group list` / `kubectl --context aks-portfolio-dev
>    get nodes`. Teardown was **prepared but not executed**
>    (`docs/runbooks/azure-teardown-runbook.md`). **Owner: P03.**
>    **→ Update 2026-10-21 (later): that second cluster was DELETED** by the
>    owner-authorised teardown — real output in
>    [`../../runbooks/azure-teardown-runbook.md`](../../runbooks/azure-teardown-runbook.md) §9;
>    see **Addendum 3**.
>
> The original status line is kept above as the author's record; the
> correction, its evidence and the current end state are in **Addendum 2**.

---

## Addendum — audit of 2026-10-21 (added by the G2 re-verification, commit `d628250`)

**This addendum does not rewrite the text above.** The claims above are the
author's, from the session of 2026-10-20/21. What follows is what a
**read-only re-check on 2026-10-21** found, so that a reader of this file
does not take the status line above at face value.

> *(Later the same day, the three over-claiming sentences above were
> **corrected in place**, each with a `corrected 2026-10-21` note quoting the
> superseded wording — the original claims are still readable here. See
> **Addendum 2**.)*

**Audit:** [`../local-platform/2026-10-20-reverify.md`](../local-platform/2026-10-20-reverify.md)
**§15.3** (same branch, `recovery/g2-20261020`).

### What the committed artifacts support

| Claim above | Committed artifact | Verdict |
|---|---|---|
| `terraform plan`: 2 to add (RG + AKS) | `terraform-plan.txt` — `Plan: 2 to add, 0 to change, 0 to destroy.` | **supported** |
| cluster `aks-portfolio-dev` in RG `rg-aks-platform-dev`, `eastasia` | the live NodeList JSON (`kubernetes.azure.com/cluster: MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia`, `agentpool: sys`, `kubelet-identity-client-id` present) | **supported** |
| `terraform apply`: "Resources: 2 added" | **none** | **no committed command output** |
| `terraform destroy` complete; `az aks show`/`az group show` → `ResourceNotFound` | **none** | **no committed command output** — but **confirmed today** by read-only `az` (below) |
| "kubectl get nodes: **3 nodes Ready (control-plane + 2 workers), v1.36.1**" | `kubectl-nodes.txt` — **ONE** node, `aks-sys-78835839-vmss000000`, ROLES `<none>`, **v1.36.4** | **contradicted by the file committed beside it**; the plan's `default_node_pool` has `node_count = 1`, `auto_scaling_enabled = false` |
| "all kube-system addons Running" | `kubectl-pods.txt` — 18 pods `Running`, but `metrics-server-749b4dd978-drrtj 1/2` and `-pmg6l 1/2` are **not Ready**; "kube-proxy x2" matches one pod; "metrics-server x2" matches three | **partly supported, partly contradicted** |
| test pod `portfolio-validate` created (Pending) | **none** — the string does not occur in any committed artifact | **no evidence** |

### The end state, re-confirmed read-only on 2026-10-21

```console
$ az aks show -g rg-aks-platform-dev -n aks-portfolio-dev
ERROR: (ResourceGroupNotFound) Resource group 'rg-aks-platform-dev' could not be found.
$ az aks list -o table
(no AKS clusters in this subscription)
$ az group list -o table
Name              Location       Status
----------------  -------------  --------
rg-flashsale      southeastasia  Succeeded
NetworkWatcherRG  eastasia       Succeeded
```

**The cluster is gone and nothing is left running** — that part of the status
line above is true and is now independently evidenced.

### Two things a reader must know before reusing this run

1. **The backend switch in this commit is permanent in the tree.** The
   `azurerm` backend (`rg-aks-tfstate` / `stakssre` / `tfstate` /
   `aks-sre/validation.terraform.tfstate`) was replaced by
   `backend "local" { path = "terraform.tfstate" }` in
   `terraform/aks-foundation/versions.tf`. The remote state object is now
   **orphaned**: a later `terraform apply` will not read it. Restoring the
   remote backend, or documenting it as deliberately abandoned, is an **open
   decision** (owner P03). See the evidence document §15.3(b).
2. **The `kubectl-cluster-info.txt` file is not `kubectl cluster-info`
   output.** It was a 1 MB / 22 458-line raw API dump of 8 object lists
   (NodeList, EventList, ServiceList, DaemonSetList, DeploymentList,
   ReplicaSetList, PodList, …). No secret *values* are present in it — only
   secret *names*/references and cluster identity ids — but it is raw
   evidence, not the sanitized form this repository's `.gitignore` describes.
   > **updated 2026-10-21:** the raw dump was **removed from HEAD** and replaced by
   > `kubectl-cluster-info.extract.txt` — the first 30 lines verbatim, the node facts
   > (name, node-image-version, kubelet, container runtime, Ready / MemoryPressure) and
   > an inventory of the documents it contains. The raw blob is still in the **git
   > history**; this change did **not** rewrite history.

**Nothing in this addendum changes what happened.** It changes how much
weight the status line above can carry.

---

## Addendum 2 — correction of the over-claim (added 2026-10-21, ~12:3x local)

**Added by the G2 push/re-verification slice, 2026-10-21, after the push of
`main` was prepared.** This addendum **did not rewrite** the text above at the
time it was written: the original narrative, the original status line and
Addendum 1 were all kept exactly as they were. A later pass on the same day
then **corrected the three over-claiming sentences in place** — the status
label, "No Azure resources remain running", and the "3 nodes Ready" line —
each with a `corrected 2026-10-21` note quoting the superseded wording, so
both the original claim and its correction remain readable in this document.
What follows is the **corrected statement** and the read-only evidence for it.

### A2.1 The corrected statement, in one place

| Item | The original text claimed | **The corrected statement (2026-10-21)** |
|---|---|---|
| Node count | "3 nodes Ready (control-plane + 2 workers)" | **1 node Ready** (`aks-sys-78835839-vmss000000`, `ROLES=<none>` — an agent-pool node; the node list contains **no** control-plane node) |
| Kubernetes version | "v1.36.1" | **v1.36.4** |
| `terraform plan` | "2 to add (RG + AKS), 0 change, 0 destroy" | **unchanged — SUPPORTED** by the committed `terraform-plan.txt` |
| `terraform apply` | "Apply complete! Resources: 2 added" | **no committed command output** → **`AZURE_CLOUD_APPLY_NOT_VERIFIED`** |
| `terraform destroy` | "complete; `az aks show`/`az group show` → `ResourceNotFound`" | **no committed command output** → **NOT VERIFIED by an artifact** (the *first* cluster's destruction was confirmed read-only on 2026-10-21 ~10:5x–11:0x, before a second cluster was created — see §15.5(a) of the local-platform evidence document) |
| Test pod | "`portfolio-validate` created (Pending)" | **no evidence** — the string does not occur in any committed artifact |
| **Overall label** | `AZURE_CLOUD_VERIFIED` | **`AZURE_CLOUD_PLAN_VERIFIED` / `AZURE_CLOUD_APPLY_NOT_VERIFIED`** |
| "No Azure resources remain running" | "All Azure resources released" | **FALSE at the time of this correction** — a **second** `aks-portfolio-dev` was **live and billable** (§A2.2). **→ TRUE again since 2026-10-21: that cluster was DELETED** (owner-authorised teardown, §A2.4 / **Addendum 3**) |

### A2.2 The end state at ~12:2x–12:3x on 2026-10-21 — since **destroyed** (2026-10-21)

> **This section records the state at ~12:2x–12:3x on 2026-10-21, when the
> second cluster was still live. It was deleted later the same day — see
> §A2.4 / Addendum 3.**

```console
$ az aks list -o table
Name               Location    ResourceGroup        KubernetesVersion    CurrentKubernetesVersion    ProvisioningState    Fqdn
aks-portfolio-dev  eastasia    rg-aks-platform-dev  1.36                 1.36.4                      Succeeded            aksportfoliodev-99hyn1lm.hcp.eastasia.azmk8s.io

$ az group list -o table
Name                                               Location       Status
-------------------------------------------------  -------------  --------
rg-flashsale                                       southeastasia  Succeeded
NetworkWatcherRG                                   eastasia       Succeeded
rg-aks-platform-dev                                eastasia       Succeeded
MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia  eastasia       Succeeded

$ kubectl --context aks-portfolio-dev get nodes
NAME                          STATUS   ROLES    AGE   VERSION
aks-sys-13411604-vmss000000   Ready    <none>   112m  v1.36.4
```

**The `terraform destroy` of the *first* cluster really did happen** — that
part of the original narrative is true and was confirmed read-only earlier
today (the resource group was `ResourceGroupNotFound` at ~10:5x–11:0x, see
§15.5(a) of
[`../local-platform/2026-10-20-reverify.md`](../local-platform/2026-10-20-reverify.md)).
**But the sentence "No Azure resources remain running" describes a state that
no longer holds.** A **later** run created a cluster with the **same name** and
**stopped one step short of the destroy**, deliberately, because it was serving
validation:

```console
$ kubectl --context aks-portfolio-dev get pods -A | grep -v kube-system
default       azure-validate                                         0/1     Pending   0          17m
```

**Consequence at the time (2026-10-21 ~12:3x): `aks-portfolio-dev` /
`rg-aks-platform-dev` were BILLABLE right then.** The teardown was
**prepared but NOT executed** — see
[`../../runbooks/azure-teardown-runbook.md`](../../runbooks/azure-teardown-runbook.md)
(commit `984c4bc`) and the pre-stop inventory under
[`../azure/2026-10-21-prestop/`](../azure/2026-10-21-prestop/).
**Owner: P03.** That slice did **not** execute any cloud mutation — every `az`
and `kubectl` call above is read-only.

**→ Update 2026-10-21 (later): the owner authorised the teardown and it was
executed. The cluster, the resource group and the `MC_…` resource group are
now deleted, and the kubeconfig context was removed. See §A2.4 below.**

### A2.3 What this correction does **not** change

- It does not change what happened on 2026-10-20/21. A cluster was created,
  validated and destroyed; a second one was created and left running
  (**and later destroyed on 2026-10-21 — see §A2.4**).
- It does not touch Addendum 1's audit — that audit is still correct about
  the *artifacts*; it simply does not cover the fact that the "nothing left
  running" state ended again at ~11:0x.
- It does not make the Azure path a *verified* one. The apply step still has
  no committed command output, so `AZURE_CLOUD_APPLY_NOT_VERIFIED` stands.
  The live-cluster claims of the **second** run are separately evidenced in
  [`../live-aks-azure-2026-10-21/aks-azure-evidence.md`](../live-aks-azure-2026-10-21/aks-azure-evidence.md).
- It does not delete any file, any artifact, or any previous claim. The
  original status line is still in this document, **above** — quoted in
  §A2.1 and in the `corrected 2026-10-21` note beside it.
- It does not delete history. On 2026-10-21 the three over-claiming sentences
  were **corrected in place** (status label, "No Azure resources remain
  running", and the "3 nodes Ready" line), each with a
  `corrected 2026-10-21` note quoting the superseded wording, so a reader
  sees both the original claim and its correction at the point of use.

### A2.4 The teardown was EXECUTED on 2026-10-21 — current end state

**The second cluster was deleted on 2026-10-21** with explicit owner
authorisation, following
[`../../runbooks/azure-teardown-runbook.md`](../../runbooks/azure-teardown-runbook.md)
§9, which records the real command output. Pre-stop snapshot:
[`../azure/2026-10-21-prestop/aks-show-final.json`](../azure/2026-10-21-prestop/aks-show-final.json).

| Check | Result (real output) |
|---|---|
| `az aks delete -g rg-aks-platform-dev -n aks-portfolio-dev --yes` | completed in ~270 s, no error output |
| `az aks show -g rg-aks-platform-dev -n aks-portfolio-dev` | `ERROR: (ResourceNotFound) The Resource 'Microsoft.ContainerService/managedClusters/aks-portfolio-dev' … was not found` (rc=3) |
| `az aks list -o table` | **empty** |
| `az group delete -n rg-aks-platform-dev --yes` | rc=0 in 25 s |
| `az group show -n rg-aks-platform-dev` / `-n MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | `ERROR: (ResourceGroupNotFound) … could not be found` (rc=3) for **both** |
| `az resource list -o table` | only `acrflashsalep6` (`rg-flashsale`) and `NetworkWatcher_eastasia` (`NetworkWatcherRG`) remain — **out of scope, untouched** |
| `kubectl config delete-context aks-portfolio-dev` | `deleted context aks-portfolio-dev from /Users/mainguyenbinhtan/.kube/config` |
| Terraform local state | 2 instances removed (`module.aks.azurerm_kubernetes_cluster.aks`, `module.aks.azurerm_resource_group.aks`) → `state list` empty → `terraform plan` = **`Plan: 2 to add, 0 to change, 0 to destroy.`** |

**End state: 0 Azure dev resources running → no Azure compute cost.**

**Labels are NOT upgraded by this teardown.** The `terraform apply` still has no
committed command output, so the label remains
**`AZURE_CLOUD_PLAN_VERIFIED` / `AZURE_CLOUD_APPLY_NOT_VERIFIED`**. What the
teardown adds is the **destroy** half: *verified live, then destroyed*.

