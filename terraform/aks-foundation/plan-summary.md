# AKS Foundation — plan summary (sanitized, quota recovery → Dsv6)

- Date: 2026-09-21 (recovery replan)
- Source commit: `e9d086c`
- Dir: `terraform/aks-foundation`
- Commands: `terraform init -input=false` (no `-upgrade`, reviewed lock kept — azurerm 5.6.0), `terraform fmt -check -recursive` (clean), `terraform validate` (Success), `terraform plan -refresh-only` (outputs only, **zero resource drift**), `terraform plan -no-color -input=false -out=.local/phase7a-dsv6.tfplan` (gitignored, NOT committed)
- Result: **Plan: 2 to add, 0 to change, 0 to destroy**
- Sanitization: subscription ID redacted to `<subscription-id>` in the committed `plan.txt`; full IDs only in gitignored `.local/*.tfplan`.

## Resources

| Action | Resource | Notes |
|--------|----------|-------|
| Add | `azurerm_kubernetes_cluster.aks` | `aks-portfolio-dev`, K8s 1.36, SKU tier Free, sys 2×`Standard_D4s_v6` |
| Add | `azurerm_role_assignment.aks_acr_pull` | `AcrPull` on shared ACR → kubelet identity |
| Already in state (no change) | `azurerm_resource_group.aks` | `rg-aks-platform-dev`, eastasia — preserved from partial apply |
| Read-only (no count) | `data.azurerm_container_registry.shared` | `acrflashsalep6` in `rg-flashsale-release` — read, not managed |

- Stale `.local/phase7a-system.tfplan` (D4as_v5, 3/0/0) **deleted**, never reused. Recovery plan is `.local/phase7a-dsv6.tfplan` (fresh, gitignored).
- `azurerm_kubernetes_cluster_node_pool.work` count = 0 (`enable_workload_pool=false`) → absent from plan. Cold D2s_v6 user pool belongs to a later, separately authorized step.

## SKU / shape

- `sku_tier = "Free"` (control-plane free; nodes/disks/network still bill).
- System pool `sys`: 2× `Standard_D4s_v6` (4 vCPU / 16 GiB, premiumIO, x64), VMSS, `only_critical_addons_enabled=true`, autoscale off.
- Network: plugin `azure`, policy `azure`, LB SKU `standard`, outbound `loadBalancer`.
- `node_provisioning_profile.mode = "Manual"` (no Node Auto-Provisioning — cost rule).
- RBAC enabled.

## OIDC / Workload Identity

- `oidc_issuer_enabled = true`, `workload_identity_enabled = true`.
- `oidc_issuer_url` = known after apply (exposed via output).

## Known after apply (selected)

- Cluster: `fqdn`, `node_resource_group`, `current_kubernetes_version`, `kubelet_identity`, `oidc_issuer_url`.
- Role assignment: `id`, `name`, `principal_id` (kubelet object id), `role_definition_id`, `principal_type`.

## ACR wiring

- Scope: shared registry `acrflashsalep6` (`rg-flashsale-release`) — subscription id redacted here, see local plan output for full id.
- Role: `AcrPull`, `skip_service_principal_aad_check = true` (kubelet MSI propagation).
- Registry mode untouched (classic LegacyRegistryPermissions, verified live); no new registry; admin stays disabled.
- No credentials in this file: kubeconfig outputs are `(sensitive value)` and omitted.

> Canonical copy: `docs/evidence/phase7a/plan-summary.md`. This file is a mirror for the Terraform root; update both or point here instead of duplicating.
