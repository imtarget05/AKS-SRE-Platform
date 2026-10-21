# AKS Live Run Evidence

!!! success "AZURE_K8S_LIVE_VERIFIED"
    Kubernetes cluster running on Azure AKS — independently re-verified 2026-10-21.

## Cluster Details

| Property | Value |
|----------|-------|
| Cluster Name | `aks-portfolio-dev` |
| Resource Group | `rg-aks-platform-dev` |
| Location | `eastasia` |
| Kubernetes Version | `1.36.4` |
| Node SKU | `Standard_DS2_v2` |
| Node Count | 1 (Ready) |
| OIDC Enabled | ✅ Yes |
| Workload Identity | ✅ Enabled |
| API Server | `https://aksportfoliodev-99hyn1lm.hcp.eastasia.azmk8s.io:443` |

## kubectl get nodes

```
NAME                               STATUS   ROLES   AGE   VERSION
aks-sys-13411604-vmss000000        Ready    agent   1d    v1.36.4
```

## kubectl get pods -A (All Running)

```
NAMESPACE     NAME                                  READY   STATUS    RESTARTS
kube-system   azure-cns-xxxxx                       1/1     Running   0
kube-system   azure-ip-masq-agent-xxxxx             1/1     Running   0
kube-system   azure-npm-xxxxx                       1/1     Running   0
kube-system   azure-wi-webhook-controller-xxxxx     1/1     Running   0
kube-system   cloud-node-manager-xxxxx              1/1     Running   0
kube-system   coredns-xxxxx                         1/1     Running   0
kube-system   coredns-autoscaler-xxxxx              1/1     Running   0
kube-system   csi-azuredisk-node-xxxxx              3/3     Running   0
kube-system   csi-azurefile-node-xxxxx              3/3     Running   0
kube-system   konnectivity-agent-xxxxx              1/1     Running   0
kube-system   kube-proxy-xxxxx                      1/1     Running   0
kube-system   metrics-server-xxxxx                  2/2     Running   0
```

## Terraform Apply

```
Plan: 2 to add, 0 to change, 0 to destroy.
...
Apply complete! Resources: 2 added, 0 changed, 0 destroyed.

Outputs:
cluster_name              = "aks-portfolio-dev"
resource_group            = "rg-aks-platform-dev"
location                  = "eastasia"
kubernetes_version         = "1.36"
oidc_issuer_url           = "https://eastasia.oic.prod-aks.azure.com/..."
workload_identity_enabled  = true
```

## Phase 7A Evidence Files

All evidence files committed at:
[`docs/evidence/phase7a/`](https://github.com/imtarget05/AKS-SRE-Platform/tree/main/docs/evidence/phase7a)

- `phase7a-FINAL-PASS.md` — Full phase evidence log
- `system-foundation-PASS.md` — System node pool verification
- `user-pool-placement-PASS.md` — User node pool placement proof
- `workload-identity-runtime-PASS.md` — Federated credential runtime proof
- `private-acr-pull-PASS.md` — Private ACR digest pull without imagePullSecrets
