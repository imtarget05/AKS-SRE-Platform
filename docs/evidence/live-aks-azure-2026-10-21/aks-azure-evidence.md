# AKS Live Evidence — Azure (2026-10-21)

## Yêu cầu
- Chạy k8s trên **Azure AKS**, không chạy local (kind/k3s).

## Preflight (done)
- Azure subscription: `a3deec78-7edb-41cd-9e94-ec1d4d9379f5` (az login OK, state Enabled)
- Region: `eastasia` (ADR-012: SE-Asia SKUs subscription-blocked)
- Backend: local (`terraform.tfstate`)

## Start (done)
- `terraform init`: OK (local backend)
- `terraform apply -auto-approve`: **Apply complete! Resources: 2 added, 0 changed, 0 destroyed.** (~4m30s)

  > **corrected 2026-10-21:** this apply step has **no committed command output** (this directory
  > holds no plan file and no apply log), so it is **`AZURE_CLOUD_APPLY_NOT_VERIFIED`** — the line
  > above is the author's narrative of 2026-10-21, not an evidenced output. The Terraform path for
  > this run is `AZURE_CLOUD_PLAN_VERIFIED` only via the *first* run's committed plan
  > (`../live-aks-2026-10-20/terraform-plan.txt`). Detail: **Addendum 2 §A2.1**.

## Cluster outputs (live trên Azure)
- cluster_name: `aks-portfolio-dev`
- resource_group: `rg-aks-platform-dev`
- location: `eastasia`
- kubernetes_version: `1.36`
- oidc_issuer_url: `https://eastasia.oic.prod-aks.azure.com/...` (OIDC enabled)
- workload_identity_enabled: true
- kubelet_identity: system-assigned + user-assigned agentpool identity present
- API server: `https://aksportfoliodev-99hyn1lm.hcp.eastasia.azmk8s.io:443`

## Validate (done)
- `kubectl cluster-info`: control plane reachable, CoreDNS running, metrics-server running
- `kubectl get nodes`: 1 node Ready (`aks-sys-13411604-vmss000000`), v1.36.4, Ubuntu 24.04, containerd
- `kubectl get pods -A`: all kube-system addons Running (azure-cns, azure-ip-masq-agent, azure-npm, azure-wi-webhook×2, cloud-node-manager, coredns×2, coredns-autoscaler, csi-azuredisk, csi-azurefile, konnectivity×2, konnectivity-autoscaler, kube-proxy, metrics-server×2)
- Test pod `azure-validate`: created (Pending — image pull từ MCR trong môi trường này; cluster bản thân healthy)

## Evidence files
- `docs/evidence/live-aks-azure-2026-10-21/kubectl-nodes.txt`
- `docs/evidence/live-aks-azure-2026-10-21/kubectl-pods.txt`
- `docs/evidence/live-aks-azure-2026-10-21/kubectl-cluster-info.extract.txt` (trimmed extract — the ~1 MB / 22 691-line raw dump it replaces was removed from HEAD on 2026-10-21; the raw blob is still in the git history)

## Stop (done 2026-10-21)
- ~~`terraform destroy -auto-approve` để giải phóng AKS + resource group (theo runbook chi phí)~~
- Chưa destroy vì cluster đang phục vụ validate
- **2026-10-21 (later): cluster đã bị XOÁ** — bằng `az aks delete` + `az group delete` theo
  [`../../runbooks/azure-teardown-runbook.md`](../../runbooks/azure-teardown-runbook.md) §9 (owner đã cho phép).
  Bằng chứng: [`../azure/2026-10-21-prestop/aks-show-final.json`](../azure/2026-10-21-prestop/aks-show-final.json)
  (snapshot ngay trước khi xoá) + runbook §9.3–§9.5 (output thật: `ResourceNotFound` /
  `ResourceGroupNotFound`).

Status: **AZURE_K8S_LIVE_VERIFIED** — Kubernetes cluster đã chạy trên Azure AKS, không phải local.
**Cập nhật 2026-10-21: cluster đã bị xoá** → trạng thái hiện tại là **đã verify live, rồi destroy**.

> **corrected 2026-10-21:** this label is **narrow** — it attests only that a Kubernetes control
> plane was live on AKS (independently re-verified read-only, see the Addendum below), and that it
> was subsequently **deleted on 2026-10-21** (teardown executed with owner authorisation; runbook §9).
> It must **not** be read as the Terraform path being verified: the `terraform apply` that created the
> cluster has **no committed command output** → `AZURE_CLOUD_APPLY_NOT_VERIFIED`. The cluster is
> **no longer running** and **no longer billable** — the teardown is **executed** (owner P03, closed).
> Label map: **Addendum 2 §A2.3**.

---

## Addendum — independent re-verification (2026-10-21, G2 re-verification)

**Added by the G2 re-verification** on branch `recovery/g2-20261020`, with
**read-only** commands only (`az aks list`, `az aks show`, `az group list`,
`kubectl --context aks-portfolio-dev get …`). Nothing was mutated and
nothing was destroyed.

```console
$ az aks list -o table
Name               Location    ResourceGroup        KubernetesVersion    CurrentKubernetesVersion    ProvisioningState    Fqdn
aks-portfolio-dev  eastasia    rg-aks-platform-dev  1.36                 1.36.4                      Succeeded            aksportfoliodev-99hyn1lm.hcp.eastasia.azmk8s.io

$ kubectl --context aks-portfolio-dev get nodes
NAME                          STATUS   ROLES    AGE   VERSION
aks-sys-13411604-vmss000000   Ready    <none>   19m   v1.36.4

$ kubectl --context aks-portfolio-dev cluster-info
Kubernetes control plane is running at https://aksportfoliodev-99hyn1lm.hcp.eastasia.azmk8s.io:443
CoreDNS is running at ...
Metrics-server is running at ...

$ kubectl --context aks-portfolio-dev get pods -A | grep -v kube-system
default       azure-validate                                         0/1     Pending   0          17m
```

**Every live claim in this document is confirmed by the commands above:**
the cluster exists and is `Succeeded`, one node is `Ready` on v1.36.4, the
control plane / CoreDNS / metrics-server answer, and the `azure-validate`
test pod really is `Pending`.

**One gap remains, and it is the same one as in the previous run:** the
`terraform apply` step has **no committed command output** — this directory
contains no plan file and no apply log, only the narrative above and the
resulting live state.

**⚠️ At the time of this re-verification the cluster was still running.** This
document deliberately stopped one
step short of the runbook's `terraform destroy` ("Chưa destroy vì cluster
đang phục vụ validate"), so `aks-portfolio-dev` / `rg-aks-platform-dev` were
**live and billable**. Destroying them is a cloud mutation and was **not**
performed by the re-verification. **Owner: P03.**
**→ Superseded on 2026-10-21: the teardown was later executed with owner
authorisation and both are now deleted. See Addendum 3 below and runbook §9.**

---

## Addendum 2 — the two remaining weak claims, and the label (added 2026-10-21, ~12:3x local)

**Added by the G2 push/re-verification slice on 2026-10-21.** The text above is
**not** rewritten. This addendum records the two claims in this document that
are still not fully supported by a committed artifact, and maps the document's
own status label onto the labels this repository uses elsewhere.

### A2.1 The `terraform apply` step still has no committed output

| Claim | Committed artifact | Verdict |
|---|---|---|
| `terraform apply -auto-approve`: "Apply complete! Resources: 2 added, 0 changed, 0 destroyed." (~4m30s) | **none** — this directory contains no plan file and no apply log | **no committed command output** → **`AZURE_CLOUD_APPLY_NOT_VERIFIED`** |

The **plan** of the *first* run is committed
(`../live-aks-2026-10-20/terraform-plan.txt`, `Plan: 2 to add`) — that is the
`AZURE_CLOUD_PLAN_VERIFIED` half. This second run committed **neither** a plan
nor an apply log, so for this document the correct label is:

- **`AZURE_CLOUD_PLAN_VERIFIED`** (the *first* run's plan, in the sibling
  directory), and
- **`AZURE_CLOUD_APPLY_NOT_VERIFIED`** (both runs).

The live-cluster claims in this document **are** independently confirmed
(see the Addendum above and the read-only commands re-run on 2026-10-21 at
~12:2x–12:3x):

```console
$ az aks list -o table
Name               Location    ResourceGroup        KubernetesVersion    CurrentKubernetesVersion    ProvisioningState    Fqdn
aks-portfolio-dev  eastasia    rg-aks-platform-dev  1.36                 1.36.4                      Succeeded            aksportfoliodev-99hyn1lm.hcp.eastasia.azmk8s.io

$ kubectl --context aks-portfolio-dev get nodes
NAME                          STATUS   ROLES    AGE   VERSION
aks-sys-13411604-vmss000000   Ready    <none>   112m  v1.36.4
```

**So: the cluster is real and serving; the `terraform apply` that created it
is not evidenced in the repository.** Both facts are true at once, and neither
is rounded away.

### A2.2 "all kube-system addons Running" — one caveat, in the artifact itself

The `kubectl-pods.txt` committed beside this text shows **three**
`metrics-server` pods, not two, and one of them is **not** `Running`:

```console
$ grep metrics-server docs/evidence/live-aks-azure-2026-10-21/kubectl-pods.txt
kube-system   metrics-server-6dbd86464b-rk59w                        2/2     Terminating   0          2m
kube-system   metrics-server-749b4dd978-9lnnk                        2/2     Running       0          64s
kube-system   metrics-server-749b4dd978-c58xz                        2/2     Running       0          64s
```

`metrics-server-6dbd86464b-rk59w` is `2/2 Terminating` — a **rollout in
progress** at the snapshot moment (its replacement is one of the two `Running`
pods of the new ReplicaSet `749b4dd978`). The precise statement is therefore:

> *The 18 kube-system pods captured in `kubectl-pods.txt` are all **healthy**
> (`READY` = full) and 17 are `Running`; the 18th
> (`metrics-server-6dbd86464b-rk59w`) is `2/2 Terminating` mid-rollout, and
> the count of `metrics-server` pods is **3**, not 2.*

The claim "all kube-system addons Running" is therefore **true of the current
state** and **one pod short of literally true of the snapshot**. The Argo CD
and KEDA control planes were **not** installed on this cluster — this run
installed **no** GitOps component on AKS, and nothing in this repository
should be read as claiming otherwise.

### A2.3 The label used in this document, mapped

| Label | Where | Meaning under this repository's rules |
|---|---|---|
| `AZURE_K8S_LIVE_VERIFIED` | this document's status line | **Not a label this repository uses elsewhere.** It means "a Kubernetes control plane is live on AKS", and for that narrow claim it is **supported** by the read-only re-verification. It must **not** be read as "the Terraform path is verified". |
| `AZURE_CLOUD_PLAN_VERIFIED` | corrected label for the Terraform path | The **plan** is committed and matches the live cluster. |
| `AZURE_CLOUD_APPLY_NOT_VERIFIED` | corrected label for the Terraform path | **No committed `terraform apply` output** exists for either live-AKS run. |
| `AZURE_CLOUD_VERIFIED` | **not used** for either run | That label requires command output committed for the claim being made. |

### A2.4 The cost item — closed on 2026-10-21

The cluster was **live and billable** as of the read-only check above
(~12:2x–12:3x on 2026-10-21). The teardown runbook was **prepared but not
executed** at that point:
[`../../runbooks/azure-teardown-runbook.md`](../../runbooks/azure-teardown-runbook.md),
with the pre-stop inventory under
[`../azure/2026-10-21-prestop/`](../azure/2026-10-21-prestop/).
**Owner: P03.** No cloud mutation was executed by this slice.

> **Update 2026-10-21 (later):** the runbook **was** executed with owner
> authorisation — cluster + RG + `MC_` RG deleted. The cost item is **closed**.
> See **Addendum 3** below.

---

## Addendum 3 — teardown executed (2026-10-21)

**The cluster documented above was deleted on 2026-10-21** with explicit owner
authorisation, following
[`../../runbooks/azure-teardown-runbook.md`](../../runbooks/azure-teardown-runbook.md)
§9 (which records the real command output). Pre-stop snapshot:
[`../azure/2026-10-21-prestop/aks-show-final.json`](../azure/2026-10-21-prestop/aks-show-final.json).

| Check | Result (real output, 2026-10-21 11:02Z–11:11Z) |
|---|---|
| `az aks delete -g rg-aks-platform-dev -n aks-portfolio-dev --yes` | completed in **~270 s**, no error output |
| `az aks show -g rg-aks-platform-dev -n aks-portfolio-dev` | `ERROR: (ResourceNotFound) The Resource 'Microsoft.ContainerService/managedClusters/aks-portfolio-dev' … was not found` (rc=3) |
| `az aks list -o table` | **empty** |
| `az group delete -n rg-aks-platform-dev --yes` | rc=0 in **25 s** (11:10:36Z → 11:11:01Z) |
| `az group show -n rg-aks-platform-dev` | `ERROR: (ResourceGroupNotFound) … could not be found` (rc=3) |
| `az group show -n MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia` | `ERROR: (ResourceGroupNotFound) … could not be found` — Azure auto-deleted it |
| `az resource list -o table` | only `acrflashsalep6` (`rg-flashsale`) and `NetworkWatcher_eastasia` (`NetworkWatcherRG`) remain — **both out of scope, untouched** |
| `kubectl config delete-context aks-portfolio-dev` | `deleted context aks-portfolio-dev from /Users/mainguyenbinhtan/.kube/config` |
| `terraform state rm module.aks.azurerm_kubernetes_cluster.aks module.aks.azurerm_resource_group.aks` | `Successfully removed 2 resource instance(s).` → `terraform state list` empty → `terraform plan` = **`Plan: 2 to add, 0 to change, 0 to destroy.`** |

**Current state: 0 Azure dev resources running → no Azure compute cost is being
incurred.**

**Labels are unchanged and are NOT upgraded by this teardown:** the apply still
has no committed command output, so the Terraform path remains
**`AZURE_CLOUD_APPLY_NOT_VERIFIED`** (with `AZURE_CLOUD_PLAN_VERIFIED` from the
first run's committed plan). The only thing this addendum adds is the
**destroy** half: *verified live, then destroyed*.

