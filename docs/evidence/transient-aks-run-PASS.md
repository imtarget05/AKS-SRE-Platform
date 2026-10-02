# Transient AKS Validation Run — PASS (2026-10-02)

- **Date:** 2026-10-02
- **Cluster:** `aks-portfolio-dev` (Kubernetes v1.36.4, SKU Tier: Free)
- **Region:** `eastasia`
- **Resource Group:** `rg-aks-platform-dev`
- **Subscription:** `a3deec78-7edb-41cd-9e94-ec1d4d9379f5`
- **Runtime Envelope:** 4 vCPU (1 system node `Standard_D2s_v6` + 1 user node `Standard_D2s_v6`) within regional ceiling of 10 vCPU.

---

## 1. Measured Quota & Cost Envelope

Pre-flight usage measured before apply:
```text
Standard Dsv6 Family vCPUs: 0 / 10
Total Regional vCPUs:       0 / 10
```

Active run usage measured during validation:
```text
Standard Dsv6 Family vCPUs: 4 / 10
Total Regional vCPUs:       4 / 10
```

- **Execution duration:** ~25 minutes total
- **Estimated compute spend:** < $0.15
- **Teardown post-condition:** Restored to `0 / 10` vCPU.

---

## 2. Infrastructure & Placement Verification

### Node Topology
```text
NAME                           STATUS   ROLES    AGE     VERSION   INTERNAL-IP   OS-IMAGE             CONTAINER-RUNTIME
aks-sys-12535438-vmss000000    Ready    <none>   10m     v1.36.4   10.224.0.4    Ubuntu 24.04.5 LTS   containerd://2.3.5-2
aks-work-19340591-vmss000000   Ready    <none>   8m      v1.36.4   10.224.0.33   Ubuntu 24.04.5 LTS   containerd://2.3.5-2
```

### System vs. User Pool Isolation
- **System Pool (`aks-sys-...`)**: Houses strictly system components (`kube-system` CoreDNS, Azure CNI, Konnectivity, Metrics Server). Exactly 0 portfolio workloads.
- **Workload Pool (`aks-work-...`)**: Houses all tenant workloads (`sre-platform/sre-demo-api`, `sre-platform/mock-dependency`, `phase7a-proof/wi-proof`).

---

## 3. Microsoft Entra Workload Identity (Secretless Auth)

- **Managed Identity:** `mi-aks-wi-proof-dev` (`a4072d9d-75c7-4f39-b864-7f07c981c67d`)
- **OIDC Issuer:** `https://eastasia.oic.prod-aks.azure.com/aa79a92c-ec09-4de1-baa9-151b8f9df886/bfd897eb-3827-4e1e-bbc2-5397e8be57d0/`
- **Federated Credential:** `wi-proof-fic` (subject: `system:serviceaccount:phase7a-proof:wi-proof`, audience: `api://AzureADTokenExchange`)
- **RBAC:** `Reader` scoped strictly to `rg-aks-platform-dev`

### In-Pod Webhook Injection Evidence
```text
AZURE_AUTHORITY_HOST=https://login.microsoftonline.com/
AZURE_CLIENT_ID=a4072d9d-75c7-4f39-b864-7f07c981c67d
AZURE_TENANT_ID=aa79a92c-ec09-4de1-baa9-151b8f9df886
AZURE_FEDERATED_TOKEN_FILE=/var/run/secrets/azure/tokens/azure-identity-token
```

### Federated Login & ARM Query Output
```json
[
  {
    "cloudName": "AzureCloud",
    "homeTenantId": "aa79a92c-ec09-4de1-baa9-151b8f9df886",
    "id": "a3deec78-7edb-41cd-9e94-ec1d4d9379f5",
    "isDefault": true,
    "name": "Azure subscription 1",
    "state": "Enabled",
    "tenantId": "aa79a92c-ec09-4de1-baa9-151b8f9df886",
    "user": {
      "name": "a4072d9d-75c7-4f39-b864-7f07c981c67d",
      "type": "servicePrincipal"
    }
  }
]
{
  "location": "eastasia",
  "name": "rg-aks-platform-dev",
  "provisioningState": "Succeeded"
}
```
**Conclusion:** Zero secrets, zero long-lived passwords or certificates. The pod authenticates directly via Kubernetes projected ServiceAccount token exchanged with Microsoft Entra ID.

---

## 4. Private ACR Pull by Immutable Digest

- **Registry:** `acrportfoliodev01.azurecr.io` (Basic tier, admin credentials disabled)
- **Role Assignment:** `AcrPull` on ACR scope assigned to AKS Kubelet Managed Identity (`7ec8ac11-2963-44c3-8b2f-19f63d680334`).
- **Workload Spec:** `imagePullSecrets: []` (no pull secret in namespace or deployment).
- **Image Digest Reference:**
  `acrportfoliodev01.azurecr.io/sre-demo-api@sha256:253087111baf7e40b472f20d695482f6c7a6700b6a9b6d45aea918e5b5a963bb`
- **Kubelet Event:**
  `Successfully pulled image "acrportfoliodev01.azurecr.io/sre-demo-api@sha256:..." in 3.8s.`

---

## 5. Workload Runtime, Probes & Failure Injection

Deployed overlay: `deploy/overlays/validation`

### Probe & Traffic Separation
1. **Liveness (`/health/live`)**:
   - `HTTP 200 {"status":"live","uptime_s":16.211}`
   - Independent of external dependencies.
2. **Readiness (`/health/ready`)**:
   - `HTTP 200 {"status":"ready","dependency":true}`
   - Validates reachability to `mock-dependency:80`.
3. **Failure Injection (`/api/fail`)**:
   - `HTTP 500 {"route":"/api/fail","status":500,"error":"injected"}`
   - Confirms that failure injection is armed in the validation overlay.
4. **RED Metrics (`/metrics`)**:
   - `sre_api_requests_total`, `sre_api_request_duration_seconds` exposed in Prometheus format.
5. **NetworkPolicy Enforcement**:
   - Default deny with explicit allow rules enforced by Azure NetworkPolicy engine.
   - Unauthorized traffic from leaf pods blocked by policy.
