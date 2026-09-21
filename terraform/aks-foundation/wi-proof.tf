# Phase 7A.2 — TEMPORARY Workload Identity proof infrastructure.
# Gated by enable_wi_proof (default false). When true, creates ONLY:
#   1. temp User Assigned Managed Identity (mi-aks-wi-proof-dev)
#   2. Federated Identity Credential (issuer = LIVE AKS OIDC issuer from state,
#      audience api://AzureADTokenExchange, subject for SA phase7a-proof/wi-proof)
#   3. Reader role assignment scoped ONLY to the existing shared ACR.
# enable_wi_proof=false destroys all three. NEVER touches AKS/RG/ACR/AcrPull.
resource "azurerm_user_assigned_identity" "wi_proof" {
  count               = var.enable_wi_proof ? 1 : 0
  name                = "mi-aks-wi-proof-dev"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name

  tags = {
    environment = "portfolio"
    owner       = "student"
    purpose     = "phase-7a-temporary-wi-proof"
    cost-mode   = "temporary"
  }
}

resource "azurerm_federated_identity_credential" "wi_proof" {
  count                     = var.enable_wi_proof ? 1 : 0
  name                      = "wi-proof-fic"
  user_assigned_identity_id = azurerm_user_assigned_identity.wi_proof[0].id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  subject                   = "system:serviceaccount:phase7a-proof:wi-proof"
}

resource "azurerm_role_assignment" "wi_proof_reader" {
  count                = var.enable_wi_proof ? 1 : 0
  scope                = data.azurerm_container_registry.shared.id
  role_definition_name = "Reader"
  principal_id         = azurerm_user_assigned_identity.wi_proof[0].principal_id

  skip_service_principal_aad_check = true
}
