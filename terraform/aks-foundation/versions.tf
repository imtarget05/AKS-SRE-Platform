terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }

  # Configuration values are provided via backend-remote.tfbackend.
  # Before any cloud apply/destroy, inspect inventory and review saved plan (P03).
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
  use_oidc = true
}
