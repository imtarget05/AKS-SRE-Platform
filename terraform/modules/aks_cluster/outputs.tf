output "resource_group_name" {
  value = azurerm_resource_group.aks.name
}

output "cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "cluster_id" {
  value = azurerm_kubernetes_cluster.aks.id
}

output "kubernetes_version" {
  value = azurerm_kubernetes_cluster.aks.kubernetes_version
}

output "oidc_issuer_url" {
  value = azurerm_kubernetes_cluster.aks.oidc_issuer_url
}

output "oidc_issuer_enabled" {
  value = azurerm_kubernetes_cluster.aks.oidc_issuer_enabled
}

output "workload_identity_enabled" {
  value = azurerm_kubernetes_cluster.aks.workload_identity_enabled
}

output "system_pool_vm_size" {
  value = azurerm_kubernetes_cluster.aks.default_node_pool[0].vm_size
}

output "kubelet_identity" {
  value       = azurerm_kubernetes_cluster.aks.kubelet_identity
  description = "The Kubelet Managed Identity block for the AKS cluster."
}

output "resource_group_id" {
  value = azurerm_resource_group.aks.id
}
