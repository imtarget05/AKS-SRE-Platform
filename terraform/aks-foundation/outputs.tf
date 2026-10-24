output "resource_group_name" {
  value = module.aks.resource_group_name
}

output "cluster_name" {
  value = module.aks.cluster_name
}

output "aks_cluster_name" {
  value       = module.aks.cluster_name
  description = "Alias for cluster_name used by deployment workflows."
}

output "cluster_id" {
  value = module.aks.cluster_id
}

output "kubernetes_version" {
  value = module.aks.kubernetes_version
}

output "oidc_issuer_url" {
  value = module.aks.oidc_issuer_url
}

output "kubelet_identity" {
  value       = module.aks.kubelet_identity
  description = "Kubelet Managed Identity block for the AKS cluster."
}

output "resource_group_id" {
  value       = module.aks.resource_group_id
  description = "Resource group ID for scoping proof role assignments."
}
