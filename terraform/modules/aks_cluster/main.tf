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
    vm_size                      = var.system_pool_vm_size
    type                         = "VirtualMachineScaleSets"
    only_critical_addons_enabled = true
    auto_scaling_enabled         = true
    min_count                    = var.system_pool_node_count
    max_count                    = 3
  }

  identity {
    type = "SystemAssigned"
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  node_provisioning_profile {
    mode = "Manual"
  }

  # AKS owns the cluster-wide autoscaler profile; defaults remain in force.
  # Do not write kube-system/cluster-autoscaler-status as configuration.

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

  lifecycle {
    precondition {
      condition = !var.workload_pool_autoscaling.enabled || (
        var.enable_workload_pool &&
        var.system_pool_node_count == 1 &&
        var.system_pool_vm_size == "Standard_D2s_v6" &&
        var.workload_pool_vm_size == "Standard_D2s_v6"
      )
      error_message = "Autoscaling requires the enabled user pool and a fixed 1xD2s_v6 system pool plus D2s_v6 user nodes to keep the declared 8-vCPU cap."
    }
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "work" {
  count                 = var.enable_workload_pool ? 1 : 0
  name                  = "work"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = var.workload_pool_vm_size
  # AzureRM node-pool docs permit an omitted node_count when autoscaling is on:
  # https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/kubernetes_cluster_node_pool
  # Let AKS own observed capacity instead of planning to undo a scale event.
  node_count           = var.workload_pool_autoscaling.enabled ? null : var.workload_pool_node_count
  mode                 = "User"
  auto_scaling_enabled = var.workload_pool_autoscaling.enabled
  min_count            = var.workload_pool_autoscaling.enabled ? var.workload_pool_autoscaling.min_nodes : null
  max_count            = var.workload_pool_autoscaling.enabled ? var.workload_pool_autoscaling.max_nodes : null
  priority             = "Regular"

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
