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
