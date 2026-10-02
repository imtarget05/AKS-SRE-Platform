terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-aks-tfstate"
    storage_account_name = "stakssre"
    container_name       = "tfstate"
    key                  = "aks-sre/validation.terraform.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  features {}
}
