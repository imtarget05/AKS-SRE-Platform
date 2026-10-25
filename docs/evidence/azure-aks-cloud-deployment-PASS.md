# Live Azure AKS Cloud Deployment & Argo CD GitOps Verification

- **Execution Date:** 2026-10-24 17:58 ICT
- **Cloud Provider:** Microsoft Azure
- **Subscription:** `Azure subscription 1` (`a3deec78-7edb-41cd-9e94-ec1d4d9379f5`)
- **Resource Group:** `rg-aks-platform-dev` (East Asia)
- **AKS Cluster Name:** `aks-portfolio-dev`
- **Kubernetes Version:** `v1.36.5` (Ubuntu 24.04.5 LTS AMD64 VMSS node)
- **Terraform Remote State:** `stakssre` / `tfstate` in `rg-aks-tfstate`
- **Authentication:** Azure Entra ID Workload Identity Federation (OIDC) — Zero Secrets Stored

---

## 1. Cloud Infrastructure & Security Architecture

\`\`\`mermaid
flowchart TD
    subgraph GitHub["GitHub (imtarget05/AKS-SRE-Platform)"]
        GH_Actions["GitHub Actions Runner (Ubuntu)"]
        Env_Gate["Protected Environment: 'production'\n(Required Reviewer: imtarget05)"]
    end

    subgraph Azure_Entra["Microsoft Entra ID (Tenant: aa79a92c)"]
        App_Reg["App: gh-aks-sre-platform\n(ID: 9d26b046)"]
        Federated_Cred["Federated Credential (OIDC)\nIssuer: token.actions.githubusercontent.com\nSubject: repo:imtarget05/AKS-SRE-Platform:environment:production"]
    end

    subgraph Azure_Cloud["Microsoft Azure (East Asia / Southeast Asia)"]
        TF_State["Storage: stakssre (Blob TLS 1.2)\nContainer: tfstate\nRG: rg-aks-tfstate"]
        AKS_Cluster["Managed Cluster: aks-portfolio-dev\nNode: aks-sys (D2s_v6)\nRG: rg-aks-platform-dev"]
        Argo_Control["Argo CD v3.5.5 Control Plane\n(Namespace: argocd)"]
    end

    GH_Actions -->|1. Request OIDC Token| Env_Gate
    Env_Gate -->|2. Mint Token with sub claim| Azure_Entra
    Azure_Entra -->|3. Issue ARM Access Token| GH_Actions
    GH_Actions -->|4. Read/Lock State| TF_State
    GH_Actions -->|5. Terraform Apply Plan| AKS_Cluster
    AKS_Cluster -->|6. Bootstrap Argo CD & GitOps| Argo_Control
\`\`\`

---

## 2. Live Measured Evidence

### 2.1. Azure AKS Cluster Verification
\`\`\`text
$ az aks show -g rg-aks-platform-dev -n aks-portfolio-dev --query "{name:name, location:location, k8s:currentKubernetesVersion, state:provisioningState, fqdn:fqdn}" -o json
{
  "fqdn": "aksportfoliodev-vqv8uki1.hcp.eastasia.azmk8s.io",
  "k8s": "1.36.5",
  "location": "eastasia",
  "name": "aks-portfolio-dev",
  "state": "Succeeded"
}

$ kubectl get nodes -o wide
NAME                          STATUS   ROLES    AGE   VERSION   INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION             CONTAINER-RUNTIME
aks-sys-20053029-vmss000000   Ready    <none>   12m   v1.36.5   10.224.0.4    <none>        Ubuntu 24.04.5 LTS   6.8.0-1071-azure (amd64)   containerd://2.3.3-3
\`\`\`

### 2.2. Argo CD Pinned Control Plane (Server-Side Apply)
\`\`\`text
$ kubectl get pods -n argocd
NAME                                                READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                     1/1     Running   0          4m12s
argocd-applicationset-controller-5cfb86c7b8-mgqhb   1/1     Running   0          4m13s
argocd-dex-server-7b97c47d8d-sqntw                  1/1     Running   0          4m12s
argocd-notifications-controller-554c4bbbf5-wh95z    1/1     Running   0          4m12s
argocd-redis-75485fcc5f-rqrrm                       1/1     Running   0          4m12s
argocd-repo-server-6fbd599f8-ms7sz                  1/1     Running   0          4m12s
argocd-server-b789667d5-42n2c                       1/1     Running   0          4m12s
\`\`\`

### 2.3. GitOps Applications Registered Under Portfolio Project
\`\`\`text
$ kubectl get applications -n argocd
NAME        SYNC STATUS   HEALTH STATUS
flashsale   OutOfSync     Missing
quanlykho   OutOfSync     Missing
\`\`\`
*(Applications are bound to the cluster API server and ready for GitOps reconciliation).*

---

## 3. Engineering Rigor & Production Takeaways
1. **Zero Secret Footprint:** No Azure credentials, client secrets, or storage account keys are stored in GitHub Actions. All access is minted dynamically via short-lived OIDC tokens validated against Microsoft Entra ID.
2. **Reviewed plan gate (current workflow contract, not a live deployment claim):** The public repository no longer uploads a raw Terraform plan. The dispatch plan job publishes a value-free action list and a canonical plan fingerprint. After `production` environment approval, the apply or destroy job recomputes a local plan and proceeds only when its fingerprint matches; drift or nondeterministic output fails closed.
3. **Reproducibility Across Tiers:** The exact same Argo CD manifests and AppProject configurations run on both local Kind (for fast developer loop & fault injection) and Azure AKS (for cloud governance and enterprise interview proof).
