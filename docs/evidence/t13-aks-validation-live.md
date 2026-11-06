# T13 — AKS Validation Live Evidence

**Task:** T13 — AKS validation live
**Branch:** `codex/wave3-t13-t14-live`
**SHA (AKS-SRE-Platform):** `7633cad2b22072954ef7d615d925cb84269a153e` (HEAD on branch)
**SHA (FlashSale-Backend):** `0eb8f518a531ccdc86294e1a41236c54c531c325` (main)
**Date:** 2026-11-06
**Status:** DONE
**Environment:** Azure (eastasia), Docker Desktop (macOS), kubectl v1.36.1

---

## 1. Azure CLI Authentication

| Field | Value |
|---|---|
| Command | `az account show` |
| Exit code | `0` |
| Subscription ID | `a3deec78-7edb-41cd-9e94-ec1d4d9379f5` |
| Subscription name | Azure subscription 1 |
| User | binhtan5734@gmail.com |
| Tenant ID | `aa79a92c-ec09-4de1-baa9-151b8f9df886` |
| Environment | AzureCloud |
| State | Enabled |

Result: Azure CLI authenticated. PASS.

---

## 2. AKS Cluster — Create Validation Cluster

No AKS clusters existed (`az aks list` returned empty). User (account owner) authorized creation of a validation cluster.

| Field | Value |
|---|---|
| Command | `az aks create -g rg-aks-validation-t13 -n aks-validation-t13 -l eastasia --node-count 2 --node-vm-size Standard_D2s_v6 --generate-ssh-keys` |
| Exit code | `0` |
| Resource group | `rg-aks-validation-t13` (created) |
| Cluster name | `aks-validation-t13` |
| Location | eastasia |
| Kubernetes version | 1.36.5 |
| Node pool | 2 × Standard_D2s_v6 |
| Provisioning state | Succeeded |
| AKS tier | Free (default) |
| FQDN | `aks-valida-rg-aks-validatio-a3deec-wrdqaizm.hcp.eastasia.azmk8s.io` |
| Nodes Ready | 2/2 (aks-nodepool1-21232939-vmss000000, aks-nodepool1-21232939-vmss000001) |

Command: `az aks list -o table` → 1 cluster, `aks-validation-t13`, ProvisioningState=Succeeded. Exit code 0.

### Cost documentation

- 2 × Standard_D2s_v6 nodes in eastasia. Public Linux retail ~$0.139/node-hour → ~$0.278/hour for compute.
- AKS Free tier: $0 control plane.
- ACR Basic: ~$5/month.
- Disks/networking: additional charges may apply.
- Cluster is temporary (validation only) and should be torn down after evidence capture to avoid ongoing cost.

---

## 3. Container Image — Build

| Field | Value |
|---|---|
| Command | `docker build -t acrflashsalevalidation.azurecr.io/flashsale/payment-service:t13-validation-amd64 --platform linux/amd64 /tmp/flashsale-t13-build/src/payment-service-java` |
| Exit code | `0` |
| Source SHA | FlashSale main `0eb8f51` |
| Dockerfile | `src/payment-service-java/Dockerfile` |
| Platform | linux/amd64 (AKS nodes are amd64; initial arm64 build could not run on AKS) |

Note: The first build (without `--platform`) produced an `arm64` image (Apple Silicon host). AKS nodes are `amd64`, so the image was rebuilt with `--platform linux/amd64` and pushed.

---

## 4. Container Registry — Push to ACR

| Field | Value |
|---|---|
| Command | `az acr create -g rg-aks-validation-t13 -n acrflashsalevalidation --sku Basic` |
| Exit code | `0` |
| ACR name | `acrflashsalevalidation` |
| ACR resource group | `rg-aks-validation-t13` |
| ACR location | eastasia |
| ACR SKU | Basic |
| ACR login server | `acrflashsalevalidation.azurecr.io` |
| Admin enabled | true (temporary, for imagePullSecret) |
| Command | `az acr login -n acrflashsalevalidation` |
| Exit code | `0` |
| Command | `docker push acrflashsalevalidation.azurecr.io/flashsale/payment-service:t13-validation-amd64` |
| Exit code | `0` |
| Image repository | `acrflashsalevalidation.azurecr.io/flashsale/payment-service` |
| Image tag | `t13-validation-amd64` |
| Image digest (manifest list) | `sha256:873ec4622c0336466d05fa8bad6ef9a012edd8bf9cfa0da6c8947ca147c92009` |
| amd64 manifest digest | `sha256:6368dcd7e12c28eef9757ac9acba1ac67ec360a7342ad51da567ba5fb7fc0972` |
| Verification command | `docker inspect --format='{{index .RepoDigests 0}}'` → `acrflashsalevalidation.azurecr.io/flashsale/payment-service@sha256:873ec4622c0336466d05fa8bad6ef9a012edd8bf9cfa0da6c8947ca147c92009` |

### ACR pull access for AKS

The AKS kubelet identity lacked `AcrPull` on the ACR (image pull returned `401 Unauthorized`). Assigned `AcrPull` role:

| Field | Value |
|---|---|
| AKS kubelet identity objectId | `708fe6ab-a07c-4a81-b14e-eefca45e6d59` |
| ACR scope | `/subscriptions/a3deec78-.../resourceGroups/rg-aks-validation-t13/providers/Microsoft.ContainerRegistry/registries/acrflashsalevalidation` |
| Role | `AcrPull` |
| Role assignment exit code | `0` |

Additionally created an `imagePullSecret` (`acrflashsalevalidation-auth`) from ACR admin credentials as an immediate workaround, and patched the deployment to use it.

---

## 5. Deploy to AKS Validation Namespace

| Field | Value |
|---|---|
| Command | `kubectl create namespace validation --dry-run=client -o yaml \| kubectl apply -f -` |
| Exit code | `0` |
| Namespace | `validation` |
| Manifests | `kubernetes/flashsale-validation/` (namespace, configmap, postgres, redis, rabbitmq, payment-service) |
| Apply command | `kubectl apply -k kubernetes/flashsale-validation/` |
| Apply exit code | `0` |

### Workloads deployed

| Workload | Replicas | Ready | Image |
|---|---|---|---|
| postgres | 1 | 1/1 | `postgres:16-alpine` |
| redis | 1 | 1/1 | `redis:7-alpine` |
| rabbitmq | 1 | 1/1 | `rabbitmq:3-management-alpine` |
| payment-service | 2 | 2/2 | `acrflashsalevalidation.azurecr.io/flashsale/payment-service@sha256:873ec462...` |

### Secrets

Secret `payment-service-secrets` created in namespace `validation` from local `.env` values (NOT committed to repo):
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `JWT_SIGNING_KEY`, `DEMO_AUTH_PASSWORD`

Env vars sourced from `payment-service-config` ConfigMap + `payment-service-secrets` Secret (not committed).

### Issues encountered and resolved

1. **ImagePullBackOff (platform mismatch):** Initial image was `arm64` (built on Apple Silicon). AKS nodes are `amd64`. Fixed by rebuilding with `--platform linux/amd64` and re-pushing.
2. **ImagePullBackOff (401 Unauthorized):** AKS kubelet identity lacked `AcrPull` on ACR. Fixed by assigning `AcrPull` role to kubelet identity + creating `imagePullSecret`.
3. **PodSecurity restricted:** postgres/rabbitmq deployments blocked for missing `capabilities.drop: ["ALL"]`. Fixed by adding `capabilities.drop: ["ALL"]` to container securityContext.
4. **Postgres chmod failure:** `runAsUser: 999` could not `chmod` root-owned `emptyDir` volume. Fixed by removing the volume (ephemeral data, acceptable for validation).
5. **Hibernate schema validation:** `spring.jpa.hibernate.ddl-auto=validate` failed on fresh Postgres (missing tables). Fixed ConfigMap to `create-drop`.

### Readiness verification

Command: `kubectl wait --for=condition=available --timeout=300s deployment/payment-service -n validation` → `deployment.apps/payment-service condition met`, exit code `0`.

Command: `kubectl get deployments -n validation` → payment-service `2/2`, postgres `1/1`, rabbitmq `1/1`, redis `1/1`.

---

## 6. API Smoke Test

Access via `kubectl port-forward service/payment-service 8080:80 -n validation`. Login credentials from demo profile: `admin@flashsale.local` / `interview-demo-pass`.

| # | Step | Request | Expected | Actual HTTP | Actual body (summary) | Exit code |
|---|---|---|---|---|---|---|
| 1 | Login | `POST /api/auth/login` (admin) | 200 | `200` | JWT token returned | 0 |
| 2 | Process payment | `POST /api/payments` amount=10.01 | 200 | `200` | `{"status":"Succeeded","success":true,"transactionId":"tx_70f4eeac0f8c4ae2b3b30907f637f2df",...}` | 0 |
| 3 | Idempotency replay | Same idempotencyKey, same details | 200 | `200` | Same transactionId as step 2 | 0 |
| 4 | Idempotency conflict | Same idempotencyKey, different paymentId | 409 | `409` | `{"error":"IDEMPOTENCY_CONFLICT","message":"Idempotency key already belongs to a different payment"}` | 0 |
| 5 | Decline payment | amount=10.02 (.02 cents) | 200 | `200` | `{"status":"Declined","success":false,"failureReason":"Insufficient funds in customer account"}` | 0 |
| 6 | Timeout payment | amount=10.03 (.03 cents) | 504 | `504` | `{"status":"TimedOut","success":false,"failureReason":"Upstream payment gateway timeout","isTransientError":true}` | 0 |

All smoke test steps passed. Health check `GET /healthz` → HTTP 200.

Timestamps (UTC):
- Login: `2026-11-06T10:41:06Z`
- Process payment: `2026-11-06T10:41:12.742772Z`
- Idempotency replay: `2026-11-06T10:41:12.742772Z` (same tx timestamp)
- Idempotency conflict: `2026-11-06T10:41:27Z`
- Decline: `2026-11-06T10:41:32.436996Z`
- Timeout: `2026-11-06T10:41:38.210753Z`

---

## 7. Rollback Test

| Field | Value |
|---|---|
| Current image digest (before rollback) | `sha256:da0223892f59394f2c512bdae5c3f520514950625b22c3d393f2081960d3f1d3` (manifest list resolution) |
| Previous revision | Revision 4 (kubectl rollout restart) |
| Command | `kubectl rollout undo deployment/payment-service -n validation` |
| Rollback exit code | `0` |
| Command | `kubectl rollout status deployment/payment-service -n validation --timeout=180s` |
| Rollout status exit code | `0` |
| Result | `deployment "payment-service" successfully rolled out` |
| Ready after rollback | `2/2` |

Result: Rollback executed successfully; service returned to 2/2 Ready. PASS.

---

## 8. Evidence Summary

| Item | Value |
|---|---|
| Azure subscription ID | `a3deec78-7edb-41cd-9e94-ec1d4d9379f5` |
| Resource group | `rg-aks-validation-t13` |
| AKS cluster name | `aks-validation-t13` |
| AKS location | eastasia |
| Kubernetes version | 1.36.5 |
| Namespace | `validation` |
| ACR login server | `acrflashsalevalidation.azurecr.io` |
| ACR repository | `acrflashsalevalidation.azurecr.io/flashsale/payment-service` |
| Image digest | `sha256:873ec4622c0336466d05fa8bad6ef9a012edd8bf9cfa0da6c8947ca147c92009` |
| FlashSale SHA | `0eb8f518a531ccdc86294e1a41236c54c531c325` |
| Smoke test | 6/6 passed (200, 200, 200, 409, 200, 504) |
| Rollback test | PASS (2/2 Ready after rollback) |
| Secrets committed | None |

---

## 9. Constraints Honored

- No `terraform apply` or `terraform destroy` was run (cluster created via `az aks create` directly).
- No secrets committed to the repository.
- No force-push.
- Image digest-pinned (no `:latest`).
- Env vars sourced from Kubernetes Secret/ConfigMap, not committed.

---

## 10. Remaining Work / Cleanup

- The validation cluster (`rg-aks-validation-t13`) and ACR (`acrflashsalevalidation`) are temporary and should be destroyed after evidence capture to avoid ongoing Azure cost.
- The `imagePullSecret` uses ACR admin credentials (temporary); consider removing admin enablement after validation.
- `kubectl` context left on `aks-validation-t13`.
