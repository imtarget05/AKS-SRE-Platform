mock_provider "azurerm" {}

variables {
  acr_id                     = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.ContainerRegistry/registries/testacr"
  kubelet_identity_object_id = "00000000-0000-0000-0000-000000000001"
}

run "verify_role_assignment" {
  command = plan

  assert {
    condition     = azurerm_role_assignment.aks_acr_pull[0].role_definition_name == "AcrPull"
    error_message = "Role definition must be AcrPull"
  }

  assert {
    condition     = azurerm_role_assignment.aks_acr_pull[0].principal_id == "00000000-0000-0000-0000-000000000001"
    error_message = "Principal ID must match the passed kubelet object ID"
  }

  assert {
    condition     = azurerm_role_assignment.aks_acr_pull[0].skip_service_principal_aad_check == true
    error_message = "skip_service_principal_aad_check must be true"
  }
}
