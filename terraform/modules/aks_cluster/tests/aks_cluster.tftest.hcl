mock_provider "azurerm" {}

run "verify_system_pool_and_security" {
  command = plan

  assert {
    condition     = azurerm_kubernetes_cluster.aks.default_node_pool[0].only_critical_addons_enabled == true
    error_message = "System pool must enforce only_critical_addons_enabled taint"
  }

  assert {
    condition     = azurerm_kubernetes_cluster.aks.default_node_pool[0].vm_size == "Standard_D2s_v6"
    error_message = "System pool must use Standard_D2s_v6 for 10 vCPU quota safety"
  }

  assert {
    condition     = azurerm_kubernetes_cluster.aks.oidc_issuer_enabled == true
    error_message = "OIDC issuer must be enabled for Workload Identity"
  }

  assert {
    condition     = azurerm_kubernetes_cluster.aks.workload_identity_enabled == true
    error_message = "Workload identity must be enabled"
  }

  assert {
    condition     = azurerm_kubernetes_cluster.aks.network_profile[0].network_plugin == "azure"
    error_message = "Network plugin must be azure"
  }

  assert {
    condition     = azurerm_kubernetes_cluster.aks.network_profile[0].network_policy == "azure"
    error_message = "Network policy must be azure"
  }

  assert {
    condition     = azurerm_kubernetes_cluster.aks.sku_tier == "Free"
    error_message = "AKS control plane must be Free tier"
  }

  assert {
    condition     = azurerm_kubernetes_cluster.aks.node_provisioning_profile[0].mode == "Manual"
    error_message = "Node auto provisioning must be Manual"
  }
}

run "verify_user_workload_pool" {
  command = plan

  assert {
    condition     = length(azurerm_kubernetes_cluster_node_pool.work) == 1
    error_message = "User workload pool must be planned when enable_workload_pool is true"
  }

  assert {
    condition     = azurerm_kubernetes_cluster_node_pool.work[0].mode == "User"
    error_message = "Workload pool must be in User mode"
  }

  assert {
    condition     = azurerm_kubernetes_cluster_node_pool.work[0].vm_size == "Standard_D2s_v6"
    error_message = "Workload pool must use Standard_D2s_v6"
  }

  assert {
    condition     = azurerm_kubernetes_cluster_node_pool.work[0].node_labels["workload"] == "portfolio"
    error_message = "Workload node label must be portfolio"
  }
}
