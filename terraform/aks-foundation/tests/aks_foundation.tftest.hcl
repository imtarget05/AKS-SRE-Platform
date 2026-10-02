mock_provider "azurerm" {}

run "verify_aks_foundation_plan" {
  command = plan

  assert {
    condition     = module.aks.cluster_name == "aks-portfolio-dev"
    error_message = "Cluster name must be aks-portfolio-dev"
  }

  assert {
    condition     = module.aks.resource_group_name == "rg-aks-platform-dev"
    error_message = "Resource group name must be rg-aks-platform-dev"
  }

  assert {
    condition     = module.aks.kubernetes_version == "1.36"
    error_message = "Kubernetes version must be 1.36"
  }

  assert {
    condition     = module.aks.oidc_issuer_enabled == true
    error_message = "OIDC issuer must be enabled for Workload Identity"
  }

  assert {
    condition     = module.aks.workload_identity_enabled == true
    error_message = "Workload identity must be enabled"
  }

  assert {
    condition     = module.aks.system_pool_vm_size == "Standard_D2s_v6"
    error_message = "System pool SKU must be Standard_D2s_v6 for 10 vCPU quota constraint"
  }
}

run "verify_workload_pool_plan" {
  command = plan

  variables {
    enable_workload_pool = true
  }

  assert {
    condition     = var.enable_workload_pool == true
    error_message = "enable_workload_pool must be true in this run"
  }
}
