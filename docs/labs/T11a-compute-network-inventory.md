# T11a — Azure compute/network inventory lab (read-only)

Scope: VM, App Service, AKS, VNet, VPN, LB, Application Gateway.
Constraint: read-only / local / kind preferred. No `terraform apply`, no Azure API calls requiring credentials.
No Terraform-only resource is labelled as live operations. Live resource IDs are recorded ONLY when actually deployed — none are (AKS cluster destroyed 2026-11-05).

## Inventory and classification

| Resource | Declared in this repo? | Terraform location | Category | Classification | Live? | Live resource ID | Validation |
|---|---|---|---|---|---|---|---|
| AKS cluster | Yes | `terraform/modules/aks_cluster/main.tf` (`azurerm_kubernetes_cluster`) | T11a compute | TERRAFORM_ONLY | No | — (destroyed) | `terraform validate` + `terraform test` (mock provider) |
| AKS system node pool | Yes | `terraform/modules/aks_cluster/main.tf` (`default_node_pool`, VMSS) | T11a compute | TERRAFORM_ONLY | No | — | `terraform test` |
| AKS user/node pool ("work") | Yes | `terraform/modules/aks_cluster/main.tf` (`azurerm_kubernetes_cluster_node_pool`) | T11a compute | TERRAFORM_ONLY | No | — | `terraform test` |
| Standalone VM | No | — | T11a compute | NOT_DECLARED | No | — | Script asserts absence |
| VNet | Yes | `terraform/modules/networking/main.tf` (`azurerm_virtual_network`) | T11a network | TERRAFORM_ONLY | No | — | `terraform validate` + `terraform test` |
| Subnets (apps/monitoring/private-endpoint) | Yes | `terraform/modules/networking/main.tf` (`azurerm_subnet`) | T11a network | TERRAFORM_ONLY | No | — | `terraform test` |
| NSG + deny-all inbound/outbound rules | Yes | `terraform/modules/networking/main.tf` (`azurerm_network_security_group` + rules) | T11a network | TERRAFORM_ONLY | No | — | `terraform test` |
| Private DNS zone + VNet link | Yes | `terraform/modules/networking/main.tf` | T11a network | TERRAFORM_ONLY | No | — | `terraform test` |
| Network Watcher + NSG flow log | Yes | `terraform/modules/networking/main.tf` | T11a network | TERRAFORM_ONLY | No | — | `terraform test` |
| Standalone Load Balancer | No | — (AKS provisions a standard LB via `network_profile.load_balancer_sku`) | T11a network | NOT_DECLARED | No | — | Script asserts absence |
| VPN (Virtual Network Gateway) | No | — | T11a network | NOT_DECLARED | No | — | Script asserts absence |
| App Service / App Service Plan | No | — | T11a compute | NOT_DECLARED | No | — | Script asserts absence |
| Application Gateway | No | — | T11a network | NOT_DECLARED | No | — | Script asserts absence |

Classification rule: `TERRAFORM_ONLY` = declared in Terraform, never applied to Azure in this session. `NOT_DECLARED` = not present in active Terraform (only a comment reference in the disabled `terraform/legacy/` tree). Nothing is labelled `LIVE`.

## Topology (text diagram)

```
[azurerm_resource_group.networking]
  └─ azurerm_virtual_network (vnet)
       ├─ subnet snet-apps        + NSG (deny-all inbound/outbound) assoc
       ├─ subnet snet-monitoring  + NSG assoc
       ├─ subnet snet-private-endpoint (private endpoint policies enabled) + NSG assoc
       └─ azurerm_private_dns_zone <-> vnet link
  ├─ azurerm_network_security_group (deny-all default)
  ├─ azurerm_network_watcher + flow log -> storage account (flow_logs, Default Deny)
  └─ azurerm_storage_account (flow_logs, LRS, network_rules default_action=Deny)

[azurerm_resource_group.aks]  (separate RG)
  └─ azurerm_kubernetes_cluster (AKS)
       ├─ system pool "sys" (only_critical_addons_enabled, Manual provisioning)
       ├─ user pool "work" (optional, autoscaling-gated)
       ├─ OIDC issuer + workload identity
       ├─ network_profile: azure plugin, azure policy, standard LB, loadBalancer outbound
       └─ RBAC enabled; private_cluster_enabled variable-gated

[azurerm_resource_group.observability] (separate RG)
  └─ Log Analytics workspace + DCR + DCR association to AKS
```

## Verification (this session, local / offline)

- `terraform fmt -check -recursive`: exit 0
- `terraform validate` (5 roots: aks-foundation, modules/acr_attachment, modules/aks_cluster, modules/networking, modules/observability): all valid
- `terraform test` (5 roots): 16 passed, 0 failed (mock providers; plan assertions only — not a cloud apply)
- `python3 scripts/t11_inventory.py tf-resources`: exit 0; no `live_resources`; NOT_DECLARED includes App Service, VPN, Application Gateway, Key Vault, standalone VM, standalone LB

Evidence: commands and exit codes recorded in this session's report. CI links from the base SHA are in `docs/evidence/2026-11-06-offline-validation.md` (pr-gate run 42070399687).

## Accuracy notes

- AKS node pools are VMSS-backed (`type = "VirtualMachineScaleSets"`); no standalone `azurerm_linux_virtual_machine` is declared, so VMs are not reported as individual live VMs.
- The standard AKS load balancer is managed by AKS (`load_balancer_sku = "standard"`); no standalone `azurerm_lb` exists, so it is NOT_DECLARED rather than mislabelled as a live LB.
- The cluster was torn down on 2026-11-05 (runbook `docs/runbooks/azure-teardown-runbook.md` §9). No live resource ID is recorded anywhere in this lab.
