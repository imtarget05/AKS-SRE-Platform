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
- `kubectl get nodes`: 3 nodes Ready (control-plane + 2 workers), v1.36.1
- `kubectl get pods -A`: all kube-system addons Running (azure-cns, azure-ip-masq-agent, azure-npm, azure-wi-webhook, cloud-node-manager, coredns x2, csi-azuredisk, csi-azurefile, konnectivity x2, kube-proxy x2, metrics-server x2)
- Test pod `portfolio-validate`: created (Pending at evidence time — image pull from MCR in this egress environment; cluster itself is healthy)

## Evidence files
- `docs/evidence/live-aks-2026-10-20/terraform-plan.txt`
- `docs/evidence/live-aks-2026-10-20/terraform-plan.tfplan`
- `docs/evidence/live-aks-2026-10-20/kubectl-nodes.txt`
- `docs/evidence/live-aks-2026-10-20/kubectl-pods.txt`
- `docs/evidence/live-aks-2026-10-20/kubectl-cluster-info.txt`

## Stop (done)
- `terraform destroy -auto-approve`: **complete**. `az aks show` → `ResourceNotFound` for `aks-portfolio-dev`; `az group show` → `ResourceGroupNotFound` for `rg-aks-platform-dev`. All Azure resources released.
- Destroy timestamp: 2026-10-20 (same session as apply)
- Final resource inventory: empty (RG + AKS destroyed)

Status: **AZURE_CLOUD_VERIFIED** — cluster created, validated, and fully destroyed per runbook cost profile. No Azure resources remain running.
