# Phase 7A — AKS foundation (system pool + OPTIONAL temporary user pool).
# Ownership (ADR-011/012): Terraform owns AZURE infrastructure only.
# Helm releases, KEDA, Deployments, ingress, ArgoCD are EXPLICITLY absent here.
resource "azurerm_resource_group" "aks" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = "portfolio"
    owner       = "student"
    purpose     = "phase-7a"
    cost-mode   = "temporary"
    created-at  = "2026-09-21"
  }
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = "aksportfoliodev"
  kubernetes_version  = var.kubernetes_version
  sku_tier            = "Free" # management free; nodes/disks/network still bill

  default_node_pool {
    name       = "sys"
    node_count = var.system_pool_node_count
    vm_size    = var.system_pool_vm_size
    type       = "VirtualMachineScaleSets"
    # This default pool doubles as the SYSTEM pool: only system components may
    # schedule here, enforced by only_critical_addons_enabled (which applies the
    # CriticalAddonsOnly=true:NoSchedule taint — set it explicitly rather than
    # hand-writing node_taints so AKS keeps the taint in sync).
    only_critical_addons_enabled = true
    auto_scaling_enabled         = false # cost rule: no unattended node creation
    # no zones: keep the minimal footprint (zone-spread is a Phase 10 topic)
  }

  identity {
    type = "SystemAssigned"
  }

  # OIDC issuer + Entra Workload Identity: foundation for the 7A proof
  # (ServiceAccount → federated credential → managed identity → Entra token).
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  # azurerm 5.x requires an explicit node provisioning profile. Manual =
  # no Node Auto-Provisioning (cost rule: no unattended node creation).
  node_provisioning_profile {
    mode = "Manual"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard" # Basic LB retired 2025-09-30
    outbound_type     = "loadBalancer"
  }

  # No Container Insights workspace for 7A (cost rule): logs stay in-cluster /
  # kubectl logs. Phase 8 revisits observability deliberately.
  role_based_access_control_enabled = true

  tags = {
    environment = "portfolio"
    owner       = "student"
    purpose     = "phase-7a"
    cost-mode   = "temporary"
  }
}

# TEMPORARY user pool for the 7A placement + private ACR pull proof.
# enable_workload_pool=false removes it (deleted the same session it is used).
resource "azurerm_kubernetes_cluster_node_pool" "work" {
  count                 = var.enable_workload_pool ? 1 : 0
  name                  = "work"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = var.workload_pool_vm_size
  node_count            = 1
  mode                  = "User"
  auto_scaling_enabled  = false
  priority              = "Regular" # Spot belongs to Phase 11 experiments

  node_labels = {
    workload = "portfolio"
  }

  tags = {
    environment = "portfolio"
    owner       = "student"
    purpose     = "phase-7a-temporary"
    cost-mode   = "temporary"
  }

  lifecycle {
    # AKS will occasionally reconcile node image/taints; never fight it here.
    ignore_changes = [node_taints]
  }
}

# Shared ACR (classic LegacyRegistryPermissions — keep mode untouched, admin
# stays disabled; AKS pulls via RBAC AcrPull on the kubelet identity).
data "azurerm_container_registry" "shared" {
  name                = "acrflashsalep6"
  resource_group_name = "rg-flashsale-release"
}

resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = data.azurerm_container_registry.shared.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id

  skip_service_principal_aad_check = true
}
