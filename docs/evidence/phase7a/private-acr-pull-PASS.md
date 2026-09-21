# 7A.2 Proof 2 — Private ACR Pull — PASS (2026-09-21)

Source commit (7A.1 freeze): `e66cd0c`.

## Artifact (immutable, previously released P02)

- Registry: `acrflashsalep6` (Standard, admin **disabled**, classic
  LegacyRegistryPermissions — mode untouched).
- Image: `acrflashsalep6.azurecr.io/legacy-app:2d5d070840b06d0da28645c9774965b63b4ac783`
  (NO `latest`).
- Expected digest (ACR metadata): `sha256:671bbc4e667f4b5c5e79738f8ecee4c18dc8618d4d4047a098bd9893cb00f71e`.

## Runtime result

- Pod `acr-pull-proof` in `phase7a-proof`, pinned to `work` pool via
  `nodeSelector: {kubernetes.azure.com/agentpool: work}` →
  **1/1 Running on `aks-work-…-vmss000000`**.
- `spec.imagePullSecrets`: **empty** — no secret, no `ACR_USERNAME/PASSWORD`,
  ACR admin stays disabled.
- Runtime `.status.containerStatuses[0].imageID`:
  `…/legacy-app@sha256:671bbc4e…` — **digest matches expected** ✅.
- App log: `listening on 3000`; health probe from inside pod:
  `{"status":"healthy","version":"1.0.0"}` ✅.

## Identity mechanism (stated explicitly)

This pull used **AKS kubelet identity + Azure RBAC `AcrPull`**
(Terraform-managed `azurerm_role_assignment.aks_acr_pull`, unchanged by 7A.2).
**This is NOT Workload Identity** — no ServiceAccount, no OIDC token, no
federation was involved in the image pull path.

## Gate

SHA image pulled ✅ · no imagePullSecret ✅ · kubelet+AcrPull ✅ · digest match ✅ ·
health ✅ · ran on user pool ✅.
