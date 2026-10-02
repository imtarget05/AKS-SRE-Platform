output "role_assignment_id" {
  value = var.enable_acr_pull ? azurerm_role_assignment.aks_acr_pull[0].id : null
}
