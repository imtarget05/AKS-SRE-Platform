# Phase 7A.1 System Foundation — PASS (2026-09-21)

Source commit: `f3282a8b845a1b15284ffe260cf25721e5a6ec56`
Saved plan: `.local/phase7a-apply.tfplan` (gitignored, gate 2/0/0, shape D4s_v6/1.36/OIDC+WI/LB-standard/AcrPull).
Apply: 2026-09-21T15:44:28Z → 15:49:43Z (~5m15s). Result: **2 added, 0 changed, 0 destroyed** (exit 0).

## Terraform state

`data.azurerm_container_registry.shared`, `azurerm_resource_group.aks`,
`azurerm_kubernetes_cluster.aks`, `azurerm_role_assignment.aks_acr_pull`. No helm/app.

## AKS (live, pre-stop)

- Name/region: `aks-portfolio-dev`, eastasia. Provisioning: Succeeded. Tier: Free.
- Version: **1.36.4**. Power (then): Running.
- System pool `sys`: **2× Standard_D4s_v6**, System mode, Regular, autoscaling OFF.
- Nodes: `aks-sys-…000000` + `…000001`, both **Ready**, v1.36.4, Ubuntu 24.04, containerd 2.3.
- kube-system: all Running, 0 restarts (coredns-autoscaler, csi disk/file, konnectivity ×3, kube-proxy ×2, metrics-server ×2).
  Only early transient `FailedScheduling` (taint during provisioning) — resolved, no CrashLoop/ImagePullBackOff.
- OIDC: **enabled** — `oidcIssuerProfile.enabled = true`, issuer URL live:
  `https://eastasia.oic.prod-aks.azure.com/<tenant-id>/<issuer-id>/` (IDs withheld from committed evidence).
- Workload Identity: `securityProfile.workloadIdentity.enabled = true`. No test pod (7A.2 scope).

## Kubelet identity → ACR

- kubelet object id `87d81af5-…` (full in state only). Role assignment live: **AcrPull → acrflashsalep6** (scope check via CLI).
- ACR: Standard, admin **disabled**, classic LegacyRegistryPermissions. No secrets, no imagePullSecret.

## Managed resource group

`MC_rg-aks-platform-dev_aks-portfolio-dev_eastasia`: VMSS `aks-sys-…`, NSG, vnet, route table, Standard LB + public IP.
Portion of Terraform's single `azurerm_kubernetes_cluster` resource — not drift.

## Quota after apply

Dsv6 **8/10**, regional **8/10** (as projected) while the cluster is **Running**.

**Correction — verified 2026-09-21 after stop:** with `powerState = Stopped`, the
node VMs are deallocated, so live usage reads **`cores 0/10` and
`StandardDsv6Family 0/10`**. `az aks stop` therefore returns the vCPU quota to the
pool; quota is consumed only while the cluster is Running. It does **not** mean the
cluster disappeared.

## Independent re-verification (post-stop audit, same day)

| Claim | Verification |
|---|---|
| Cluster exists, Stopped | `az aks list` → 1 cluster, `aks-portfolio-dev` eastasia, `powerState=Stopped`, `provisioningState=Succeeded` |
| Version | `currentKubernetesVersion = 1.36.4` (pool orchestrator `1.36`) |
| Pool shape | `agentPoolProfiles` = one pool `sys`, mode System, 2× `Standard_D4s_v6`, autoscaling `False` → **no user pool** |
| ACR pull RBAC | live `AcrPull` on `acrflashsalep6` for kubelet id `87d81af5-…` ✅ (a second, older `AcrPull` principal `1dbb8786-…` exists — pre-existing, not created by this apply) |
| No compute burning | VMSS `aks-sys-26564277-vmss` capacity **0** while stopped |
| Managed RG contents | 6 resources only: VMSS, vnet, NSG, Standard LB, public IP, route table — all AKS-owned, no orphan |

- `terraform state list` = `data.azurerm_container_registry.shared`, `azurerm_resource_group.aks`,
  `azurerm_kubernetes_cluster.aks`, `azurerm_role_assignment.aks_acr_pull` — no Helm/app/monitoring.

## Outstanding provider-block drift (non-destructive, not fixed)

A post-apply `terraform plan` reports **0 to add, 1 to change, 0 to destroy**: an in-place
`azurerm_kubernetes_cluster.aks` update where the 5.6.0 provider wants to add block-level
null/empty fields it does not yet see (`default_node_pool.upgrade_settings`,
`custom_ca_trust_certificates_base64 = []`, `identity.identity_ids = []`,
`default_node_pool.zones = []`). No force-replace, no destroy, no security change.
Left unresolved deliberately: the AKS create-path bug that forced provider `~> 5.0`
(converting null/empty blocks to `[]`) makes such no-op fields **unsafe to write back**.
Recorded as debt for Phase 8, not acted on while the cluster is stopped.

## Cost accuracy note

The earlier "≈ 15:45–16:05Z ≈ 0.35h" window in this file was a **UTC** timestamp; the
apply actually ran at **22:44–22:49 local (≈15:44–15:49Z)**. Window remains ≈0.35h ×
0.554 ≈ **$0.19** compute, so the figure stands, but the timestamp framing is corrected.


## Cost footprint

- Live window (~15:45–16:05Z ≈ 0.35h × 0.554): **≈ $0.19** compute.
- While stopped: compute ≈ 0; disks + public IP + Standard LB persist (small, ongoing).

## Cluster stop

`az aks stop` → `powerState.code = Stopped` (verified). Spend is NOT zero (see above).

## Gate

2 nodes Ready ✅ · kube-system healthy ✅ · OIDC ✅ · WI foundation ✅ · AcrPull ✅ · no apps ✅ · stopped ✅.

## Explicitly NOT claimed

No user pool, no private-pull runtime proof, no WI pod proof, no Argo CD, no ingress, no P01/P02.
Next (locked): 7A.2 temp pool + proofs. STOP.
