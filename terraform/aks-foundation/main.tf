# Phase 7A — AKS foundation (system pool + OPTIONAL temporary user pool).
# Ownership (ADR-011/012/014): Terraform owns AZURE infrastructure only.
# Decoupled into reusable modules: aks_cluster and acr_attachment.

module "aks" {
  source = "../modules/aks_cluster"

  resource_group_name      = var.resource_group_name
  location                 = var.location
  cluster_name             = var.cluster_name
  kubernetes_version       = var.kubernetes_version
  system_pool_vm_size      = var.system_pool_vm_size
  system_pool_node_count   = var.system_pool_node_count
  enable_workload_pool     = var.enable_workload_pool
  workload_pool_vm_size    = var.workload_pool_vm_size
  workload_pool_node_count = 1
}

# Decoupled ACR integration boundary (gated by enable_acr_integration)
data "azurerm_container_registry" "shared" {
  count               = var.enable_acr_integration ? 1 : 0
  name                = var.acr_name
  resource_group_name = var.acr_resource_group_name
}

module "acr_attachment" {
  source = "../modules/acr_attachment"
  count  = var.enable_acr_integration ? 1 : 0

  acr_id                     = data.azurerm_container_registry.shared[0].id
  kubelet_identity_object_id = module.aks.kubelet_identity[0].object_id
  enable_acr_pull            = true
}
