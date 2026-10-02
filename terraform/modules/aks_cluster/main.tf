resource "azurerm_resource_group" "aks" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = var.environment
    owner       = "student"
    purpose     = "platform-foundation"
  }
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = var.dns_prefix
  kubernetes_version  = var.kubernetes_version
  sku_tier            = "Free"

  default_node_pool {
    name                         = "sys"
    node_count                   = var.system_pool_node_count
    vm_size                      = var.system_pool_vm_size
    type                         = "VirtualMachineScaleSets"
    only_critical_addons_enabled = true
    auto_scaling_enabled         = false
  }

  identity {
    type = "SystemAssigned"
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  node_provisioning_profile {
    mode = "Manual"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
  }

  role_based_access_control_enabled = true

  tags = {
    environment = var.environment
    owner       = "student"
    purpose     = "platform-foundation"
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "work" {
  count                 = var.enable_workload_pool ? 1 : 0
  name                  = "work"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = var.workload_pool_vm_size
  node_count            = var.workload_pool_node_count
  mode                  = "User"
  auto_scaling_enabled  = false
  priority              = "Regular"

  node_labels = {
    workload = "portfolio"
  }

  tags = {
    environment = var.environment
    owner       = "student"
    purpose     = "workload-user-pool"
  }

  lifecycle {
    ignore_changes = [node_taints]
  }
}
