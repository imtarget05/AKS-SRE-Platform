# Live Azure AKS Cluster Runtime Verification Evidence

- **Execution Date:** 2026-10-22T11:02:09+07:00
- **Subscription ID:** `a3deec78-7edb-41cd-9e94-ec1d4d9379f5` (Azure subscription 1)
- **Resource Group:** `rg-aks-platform-dev`
- **Region:** `eastasia`
- **Cluster Name:** `aks-portfolio-dev`
- **Verification Level:** **`RUNTIME_VERIFIED (LIVE_AZURE)`**
- **Terraform Duration:** 4m32s

---

## 1. Live Kubernetes Nodes (Azure VMSS)
```text
NAME                          STATUS   ROLES    AGE   VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION             CONTAINER-RUNTIME
aks-sys-40236146-vmss000000   Ready    <none>   71s   v1.36.4   10.224.0.4    <none>        Ubuntu 24.04.5 LTS   6.8.0-1071-azure (amd64)   containerd://2.3.3-3
```

## 2. Live System Pods & Workload Identity
```text
NAMESPACE     NAME                                                   READY   STATUS    RESTARTS   AGE
kube-system   azure-cns-nzr8d                                        1/1     Running   0          70s
kube-system   azure-ip-masq-agent-g9x9x                              1/1     Running   0          70s
kube-system   azure-npm-xshcb                                        1/1     Running   0          70s
kube-system   azure-wi-webhook-controller-manager-7ffcd46d64-6m7st   1/1     Running   0          84s
kube-system   azure-wi-webhook-controller-manager-7ffcd46d64-dstxj   1/1     Running   0          84s
kube-system   cloud-node-manager-bmb6l                               1/1     Running   0          70s
kube-system   coredns-76df789c68-7jnhr                               1/1     Running   0          37s
kube-system   coredns-76df789c68-gnv4c                               1/1     Running   0          84s
kube-system   coredns-autoscaler-548c6d85c6-tddcl                    1/1     Running   0          84s
kube-system   csi-azuredisk-node-qmk8x                               3/3     Running   0          70s
kube-system   csi-azurefile-node-vd657                               4/4     Running   0          70s
kube-system   konnectivity-agent-7bb6645bc4-7q2xh                    1/1     Running   0          35s
kube-system   konnectivity-agent-7bb6645bc4-gkhkg                    1/1     Running   0          81s
kube-system   konnectivity-agent-autoscaler-67f8b6cdd6-zqpsj         1/1     Running   0          81s
kube-system   kube-proxy-tqvrm                                       1/1     Running   0          70s
kube-system   metrics-server-6dbd86464b-9x9xn                        1/2     Running   0          81s
kube-system   metrics-server-749b4dd978-pvvwp                        1/2     Running   0          30s
kube-system   metrics-server-749b4dd978-rnmjd                        1/2     Running   0          30s
```

## 3. Terraform Outputs
```json
{
  "cluster_id": "/subscriptions/a3deec78-7edb-41cd-9e94-ec1d4d9379f5/resourceGroups/rg-aks-platform-dev/providers/Microsoft.ContainerService/managedClusters/aks-portfolio-dev",
  "cluster_name": "aks-portfolio-dev",
  "kubernetes_version": "1.36",
  "oidc_issuer_url": "https://eastasia.oic.prod-aks.azure.com/aa79a92c-ec09-4de1-baa9-151b8f9df886/11f3088d-0453-4f4f-a32b-4637aadd12d2/",
  "resource_group_id": "/subscriptions/a3deec78-7edb-41cd-9e94-ec1d4d9379f5/resourceGroups/rg-aks-platform-dev",
  "resource_group_name": "rg-aks-platform-dev"
}
```
