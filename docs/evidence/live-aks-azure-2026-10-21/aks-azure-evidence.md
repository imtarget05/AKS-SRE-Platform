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
- `docs/evidence/live-aks-azure-2026-10-21/kubectl-cluster-info.txt`

## Stop (tuỳ chọn)
- `terraform destroy -auto-approve` để giải phóng AKS + resource group (theo runbook chi phí)
- Chưa destroy vì cluster đang phục vụ validate

Status: **AZURE_K8S_LIVE_VERIFIED** — Kubernetes cluster đang chạy trên Azure AKS, không phải local.

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

**⚠️ The cluster is still running.** This document deliberately stopped one
step short of the runbook's `terraform destroy` ("Chưa destroy vì cluster
đang phục vụ validate"), so `aks-portfolio-dev` / `rg-aks-platform-dev` are
**live and billable**. Destroying them is a cloud mutation and was **not**
performed by the re-verification. **Owner: P03.**
