# AKS Foundation — plan summary (sanitized)

- Date: 2026-09-21
- Dir: `terraform/aks-foundation`
- Commands: `terraform fmt` (clean), `terraform validate` (Success), `terraform plan -no-color -input=false | tee plan.txt` (no `-out` file)
- Result: **Plan: 3 to add, 0 to change, 0 to destroy**

## Resources

| Action | Resource | Notes |
|--------|----------|-------|
| Add | `azurerm_resource_group.aks` | `rg-aks-platform-dev`, eastasia |
| Add | `azurerm_kubernetes_cluster.aks` | `aks-portfolio-dev`, K8s 1.36, SKU tier Free |
| Add | `azurerm_role_assignment.aks_acr_pull` | `AcrPull` on shared ACR → kubelet identity |
| Read-only (no count) | `data.azurerm_container_registry.shared` | `acrflashsalep6` in `rg-flashsale-release` — read, not managed |

- `azurerm_kubernetes_cluster_node_pool.work` count = 0 (`enable_workload_pool=false`), so absent from plan.

## SKU / shape

- `sku_tier = "Free"` (control-plane free; nodes/disks/network still bill).
- System pool `sys`: 2× `Standard_D4as_v5`, VMSS, `only_critical_addons_enabled=true`, autoscale off.
- Network: plugin `azure`, policy `azure`, LB SKU `standard`, outbound `loadBalancer`.
- `node_provisioning_profile.mode = "Manual"` (no Node Auto-Provisioning — cost rule).
- RBAC enabled.

## OIDC / Workload Identity

- `oidc_issuer_enabled = true`, `workload_identity_enabled = true`.
- `oidc_issuer_url` = known after apply (exposed via output).

## Known after apply (selected)

- Cluster: `fqdn`, `node_resource_group`, `current_kubernetes_version`, `kubelet_identity`, `oidc_issuer_url`.
- Role assignment: `id`, `name`, `principal_id` (kubelet object id), `role_definition_id`, `principal_type`.
- Outputs: `cluster_id`, `oidc_issuer_url`, `kubelet_identity_object_id` known after apply.

## ACR wiring

- Scope: shared registry `acrflashsalep6` (`rg-flashsale-release`) — subscription id redacted here, see local `plan.txt` for full id.
- Role: `AcrPull`, `skip_service_principal_aad_check = true` (kubelet MSI propagation).
- Registry mode untouched (classic LegacyRegistryPermissions, verified earlier); no new registry; admin stays disabled.
- No credentials in this file: kubeconfig outputs are `(sensitive value)` and omitted.
