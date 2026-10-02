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
5. **NetworkPolicy** — `IMPLEMENTED` / `NOT_VERIFIED`

   The four policies in `deploy/base/networkpolicy.yaml` (default-deny,
   allow-dns, sre-demo-api, mock-dependency) were applied and accepted by the
   Kubernetes API server.

   **Enforcement was NOT verified.** This cluster ran `network_plugin = "azure"`
   (classic Azure CNI) with no Cilium addon and no overlay dataplane. Per this
   repo's own `ADR-014` and the header of `deploy/base/networkpolicy.yaml`,
   enforcement requires Azure CNI **Overlay + Cilium** — neither of which was
   present. Acceptance by the API server is not evidence of a deny taking
   effect.

   Historical negative control: **INCONCLUSIVE.** The intended test — traffic
   from `mock-dependency` to `sre-demo-api:80`, which policy should block —
   was terminated before returning a result. No authoritative
   blocked/allowed outcome was obtained, so it is recorded as inconclusive
   rather than as a pass.

   ```text
   NETWORKPOLICY_OBJECTS      = IMPLEMENTED / APPLIED
   NETWORKPOLICY_ENFORCEMENT  = NOT_VERIFIED
   NEGATIVE_CONTROL_RESULT    = INCONCLUSIVE
   CILIUM                      = TARGET / NOT_VERIFIED
   ```

   Proving enforcement is a separate, explicit exercise (deploy Overlay +
   Cilium, then run the negative control to completion). It is deliberately
   **not** claimed here.


---

## 6. Teardown & Post-Condition — `VERIFIED_LIVE`

Teardown was performed immediately after validation, to return the shared
regional quota envelope to its baseline.

```text
DESTROY COMMAND LOG = NOT RETAINED
POST-TEARDOWN STATE = VERIFIED_LIVE
```

The original `terraform destroy` console output was not preserved as an
artifact, so it is not quoted or reconstructed here. What follows is a fresh,
independent re-query of live Azure state — the authoritative basis for the
teardown claim.

Re-verified at `2026-10-02T14:29:57Z` (read-only queries):

| Check | Command | Result |
|---|---|---|
| Regional vCPU | `az vm list-usage --location eastasia` | `Total Regional vCPUs 0 / 10` |
| Dsv6 family vCPU | same | `Standard Dsv6 Family vCPUs 0 / 10` |
| Cluster resource group | `az group show -n rg-aks-platform-dev` | `ResourceGroupNotFound` |
| Temporary ACR | `az acr list` | empty — `acrportfoliodev01` removed |
| Workload namespaces | `kubectl delete namespace sre-platform phase7a-proof` | deleted |

Remaining resource groups in the subscription are unrelated to this run
(`NetworkWatcherRG`, `rg-portfolio-evidence`, and the `*-tfstate` state
backends). No AKS cluster, node pool, container registry, or namespace from
this validation run remains.

```text
AKS_CLUSTER          = DESTROYED (VERIFIED_LIVE)
NODE_POOLS           = DESTROYED (VERIFIED_LIVE)
TRANSIENT_ACR        = DELETED   (VERIFIED_LIVE)
QUOTA                = 0 / 10 vCPU (VERIFIED_LIVE)
BILLABLE_RUNTIME     = NONE from this run
```

**Cost.** The `< $0.15` figure in §1 is an **estimate**, not a measured Azure
Cost Management query. No billing export was captured, so no measured spend
figure is claimed. What is measured is the compute envelope: peak 4 vCPU for
roughly 25 minutes inside a Free-tier control plane.

---

## 7. Status Summary

| Capability | Status |
|---|---|
| AKS cluster provisioning, K8s v1.36.4, Free tier | `VERIFIED_TRANSIENT` |
| System/user pool placement & isolation | `VERIFIED_TRANSIENT` |
| Private ACR pull by immutable digest, no pull secret | `VERIFIED_TRANSIENT` |
| Workload Identity federated token exchange → ARM read | `VERIFIED_TRANSIENT` |
| AcrPull via Kubelet managed identity | `VERIFIED_TRANSIENT` |
| Liveness / readiness / failure-injection routes | `VERIFIED_TRANSIENT` |
| Container non-root, read-only root filesystem | `VERIFIED_TRANSIENT` |
| Teardown to `0 / 10` vCPU | `VERIFIED_LIVE` |
| NetworkPolicy **objects applied** | `VERIFIED_TRANSIENT` |
| NetworkPolicy **enforcement** | `NOT_VERIFIED` |
| NetworkPolicy negative control | `INCONCLUSIVE` |
| Cilium / Azure CNI Overlay | `TARGET` — `NOT_VERIFIED` |
| Argo CD, Gateway API + Envoy, Prometheus, Grafana | `IMPLEMENTED_TESTED_LOCAL` (kind) — not on AKS |
| HPA / cluster autoscaler, PDB, topology spread | `NOT_VERIFIED` |

Components marked `IMPLEMENTED_TESTED_LOCAL` have passing proofs on the local
kind platform (see `docs/evidence/local-platform/`). They were **not** part of
this Azure run and are not claimed as live here.
