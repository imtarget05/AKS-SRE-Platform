# 7A.2 Proof 3 — Workload Identity Runtime — PASS (2026-09-21)

Source commit (7A.1 freeze): `e66cd0c`.

## Terraform (saved plans, gitignored; code: `terraform/aks-foundation/wi-proof.tf`)

- New file `wi-proof.tf` + `variable "enable_wi_proof"` (default false).
  Schema fix during authoring: azurerm 5.6.0 `azurerm_federated_identity_credential`
  uses `user_assigned_identity_id` (not `parent_id`, no `resource_group_name`) —
  confirmed via provider schema; `fmt` clean, `validate` Success.
- Plan (`enable_workload_pool=true`, `enable_wi_proof=true`):
  **3 add / 2 change / 0 destroy**. Adds = temp UAMI `mi-aks-wi-proof-dev` +
  FIC `wi-proof-fic` + `Reader` on ACR only. Changes = the two known no-op
  provider-block normalizations (cluster + work pool); no replacement, no destroy.
- Apply exact plan: 3 added, 0 destroyed.

## Live identity verification (before any pod)

- FIC: subject `system:serviceaccount:phase7a-proof:wi-proof` ✅,
  audience `["api://AzureADTokenExchange"]` ✅,
  **issuer == live `az aks show … oidcIssuerProfile.issuerUrl`** (compared at
  runtime, `ISSUER_MATCH: YES` — full URLs withheld from evidence) ✅.
- Role: principal holds exactly **`Reader`** on `…/registries/acrflashsalep6`
  and nothing else (queried live) ✅. Kubelet `AcrPull` untouched.

## Kubernetes objects (namespace `phase7a-proof`, since deleted)

- ServiceAccount `wi-proof` annotated
  `azure.workload.identity/client-id: 0722857d-…` (truncated; full ID in state
  only). No secret/password/token in YAML.
- Pod `wi-proof` (`mcr.microsoft.com/azure-cli:2.79.0`, `sleep infinity`):
  label `azure.workload.identity/use: "true"` ✅,
  `serviceAccountName: wi-proof` ✅, scheduled on
  `aks-work-…-vmss000000` (work pool) ✅, 1/1 Running.
- Webhook injection verified inside pod (values present, token NEVER printed):
  `AZURE_CLIENT_ID` ✅, `AZURE_TENANT_ID` ✅,
  `AZURE_FEDERATED_TOKEN_FILE=/var/run/secrets/azure/tokens/azure-identity-token`
  (non-empty file) ✅, `AZURE_AUTHORITY_HOST=https://login.microsoftonline.com/` ✅.

## Federated login + harmless read (from inside the pod)

- `az login --service-principal --username $AZURE_CLIENT_ID --tenant
  $AZURE_TENANT_ID --federated-token $(cat $AZURE_FEDERATED_TOKEN_FILE)` →
  **exit 0**. No client secret, no certificate, no storage key.
- `az acr show --name acrflashsalep6` → **SUCCESS**:
  `{name: acrflashsalep6, sku: Standard, admin: false}` ✅.

## Negative check (read-only, no destructive write)

- `az role assignment list --assignee <proof-client-id> --scope <acr-id>` →
  exactly one entry: **`Reader` on `acrflashsalep6`**. No write attempted.

## Identity mechanism (stated explicitly)

`ServiceAccount token → AKS OIDC → Microsoft Entra federation → temp UAMI →
ARM read`, with Reader scope limited to the existing ACR. No new Key Vault /
Service Bus / Storage was created for this proof. **This is a different
identity path from the kubelet-identity private ACR pull (Proof 2).**

## Cleanup

Namespace deleted (Step 15) → saved cleanup plan destroyed **strictly**
Reader role + FIC + UAMI (3 destroyed, nothing else); UAMI absence verified
live (`ResourceNotFound`). Kubelet `AcrPull` intact.

## Gate

WI ServiceAccount ✅ · required label ✅ · FIC issuer/subject/audience match ✅ ·
federated token exchange ✅ · runtime read ✅ · no secret/key/cert ✅ ·
Reader-only ✅ · all temp objects deleted ✅.
