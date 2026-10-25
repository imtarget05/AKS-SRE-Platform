# FinOps Cloud Cost Report & Architecture Telemetry (Azure AKS)

**Environment**: `aks-portfolio-dev` (Resource Group: `rg-aks-platform-dev`, Region: `eastasia`)  
**Date**: 2026-10-25  
**Cluster Architecture**: Azure Kubernetes Service (AKS v1.36.5) with Azure CNI & Managed Disks  
**Workloads Running**: FlashSale-Backend (P01), QuanLyKho (P02), Agent-Hub (Investigation Orchestrator)

---

## 1. Executive Summary & Cost Breakdown

The cloud architecture was provisioned to demonstrate a multi-tier resilient flash-sale and banking operations platform on Microsoft Azure without accumulating unnecessary runaway cloud expenses.

| Azure Resource | Tier / SKU | Specs / Allocation | Unit Rate (East Asia) | Monthly Cost (USD) |
| :--- | :--- | :--- | :--- | :--- |
| **AKS Control Plane** | Free Tier | Managed k8s API server SLA 99.9% | \$0.00 / hour | **\$0.00** |
| **AKS Worker Nodes** | Virtual Machine Scale Set (`sys`) | 2 × `Standard_D2s_v6` (4 vCPU, 16 GiB RAM total) | \$0.096 / node / hour | **\$138.24** |
| **Node OS Disks** | Managed Disks (Standard SSD E10) | 2 × 128 GiB OS Disks | \$5.80 / disk / month | **\$11.60** |
| **Stateful Data Disks** | Managed Disks (Standard SSD E1) | 2 × 1 GiB (`data-postgres-0`, `data-rabbitmq-0`) | \$0.60 / disk / month | **\$1.20** |
| **Container Registry** | Azure Container Registry (ACR) | Basic Tier (`acrflashsalep6.azurecr.io`) | \$0.167 / day | **\$5.00** |
| **Public IP & LoadBalancer**| Standard SKU | 1 Public IP (Egress/Ingress routing) | \$0.005 / hour | **\$3.60** |
| **Virtual Network & Egress**| Azure VNet | Internal cluster DNS & East Asia intra-region | < 10 GB/month | **\$0.80** |
| **Total Cloud Baseline** | — | **Full Active Cluster Operational Rate** | **~\$0.22 / hour** | **~\$160.44 / month** |

---

## 2. Resource Utilization & Pod Distribution (Live Telemetry)

As observed on `aks-portfolio-dev` on 2026-10-25:

### Node 0 (`aks-sys-20053029-vmss000000`):
- **Role**: System & Platform Control Services
- **Allocated Capacity**: 30/30 Pods (Hard Ceiling)
- **Active System Pods**:
  - `argocd`: 7 pods (`application-controller`, `server`, `repo-server`, `dex`, `redis`, `notifications`, `applicationset`)
  - `keda`: 3 pods (`operator`, `admission-webhooks`, `metrics-apiserver`)
  - `kube-system`: 18 pods (`azure-cns`, `azure-npm`, `coredns`, `metrics-server`, `csi-azuredisk`, `csi-azurefile`, `konnectivity`)
  - `agent-hub`: 1 pod (`agent-hub-7b974bb9cf-xf99k`)
  - `flashsale`: 1 pod (`redis-695b986ccc-d6jlt`)

### Node 1 (`aks-sys-20053029-vmss000001`):
- **Role**: Application Workloads & High-Performance Data Stores
- **Allocated Capacity**: 12/30 Pods (~96% requested CPU)
- **Active Workload Pods**:
  - `flashsale`:
    - `postgres-0`: 1/1 Running (attached to PVC `data-postgres-0` 1Gi)
    - `rabbitmq-0`: 1/1 Running (attached to PVC `data-rabbitmq-0` 1Gi)
    - `kafka-0`: 1/1 Running
    - `order-api-55b5dc9df-2f744`: 1/1 Running
    - `order-api-55b5dc9df-xw9qv`: 1/1 Running
    - `order-worker-58c6b9d9c7-84r5s`: 1/1 Running
    - `order-worker-58c6b9d9c7-d9wk6`: 1/1 Running
    - `payment-service-6845cd98bb-rrc4h`: 1/1 Running
  - `quanlykho`:
    - `bankops-api-746c9db96c-2jntk`: 1/1 Running
    - `bankops-api-746c9db96c-pcsdx`: 1/1 Running
    - `bankops-worker-f666857bb-nmgnl`: 1/1 Running

---

## 3. Cost-Optimization & Lifecycle Strategy

1. **Spot Instance / Ephemeral Testing Strategy**:
   - For ad-hoc performance benchmarks or fault injection drills, secondary workload nodes can be transitioned to Azure Spot Instances (`--priority Spot --max-price 0.03`), reducing worker compute cost by 70–80%.
2. **Scheduled Off-Hours Scaling**:
   - During evaluation hiatus, the nodepool count is scaled down to 0 or 1 node via `az aks nodepool scale --node-count 0`, pausing VM billing entirely while preserving disk state and Argo CD Application definitions.
3. **Cluster Teardown & Reconstruction Automation**:
   - The platform repository includes `scripts/rebuild-aks.sh` and Terraform definitions in `platform/aks-sre-platform/terraform`. The entire cluster can be destroyed and reconstructed within 12 minutes with identical certificates, OIDC bindings, and GitOps state.
