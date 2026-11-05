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
  sku_tier            = var.sku_tier

  default_node_pool {
    name                         = "sys"
    vm_size                      = var.system_pool_vm_size
    type                         = "VirtualMachineScaleSets"
    only_critical_addons_enabled = true
    node_count                   = var.system_pool_node_count
    auto_scaling_enabled         = false
    zones                        = var.zones
    upgrade_settings {
      max_surge                     = "10%"
      drain_timeout_in_minutes      = 0
      node_soak_duration_in_minutes = 0
    }
    # enable_zone_balancing = true  # not supported by azurerm v5.8.0
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
  private_cluster_enabled           = var.private_cluster_enabled

  tags = {
    environment = var.environment
    owner       = "student"
    purpose     = "platform-foundation"
  }

  lifecycle {
    precondition {
      condition     = var.system_pool_node_count >= 2 && length(var.zones) >= 2
      error_message = "Production requires ≥2 nodes across zones; confirm budget (Sacombank Q1) before apply."
    }
    precondition {
      condition     = !var.workload_pool_autoscaling.enabled || var.enable_workload_pool
      error_message = "Autoscaling requires the user workload pool to be enabled."
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

  upgrade_settings {
    max_surge                     = "10%"
    drain_timeout_in_minutes      = 0
    node_soak_duration_in_minutes = 0
  }

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
