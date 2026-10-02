# Remote state for AKS-SRE validation — PARTIAL CONFIG, no credential values.
#
#   terraform init -reconfigure -backend-config=environments/validation/backend.hcl
#
# This repository's OWN state identity. It shares nothing with MAIA, Helpdesk or
# Factory: separate resource group, separate storage account, separate key. That
# separation is the point — a typo here must not be able to reach another
# project's canonical state, and a typo there must not be able to reach this.
#
# `use_azuread_auth = true` and no `use_oidc`: see versions.tf for why a static
# OIDC flag is wrong for a shared, committed config.
resource_group_name  = "rg-aks-tfstate"
storage_account_name = "stakssre"
container_name       = "tfstate"
key                  = "aks-sre/validation.terraform.tfstate"

use_azuread_auth = true