resource "azurerm_role_assignment" "aks_acr_pull" {
  count                            = var.enable_acr_pull ? 1 : 0
  scope                            = var.acr_id
  role_definition_name             = "AcrPull"
  principal_id                     = var.kubelet_identity_object_id
  skip_service_principal_aad_check = true
}
