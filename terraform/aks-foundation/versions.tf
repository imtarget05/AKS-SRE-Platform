terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }

  # Canonical backend state ownership:
  # 1. Post-decommissioning / local verification mode: uses "local" backend.
  # 2. Cloud deployment mode: uses Azure Blob Storage via backend configuration:
  #    `terraform init -backend-config=backend-remote.tfbackend -reconfigure`
  # Before any cloud apply/destroy, inspect inventory and review saved plan (P03).
  backend "azurerm" {
    # Configuration values provided via -backend-config=backend-remote.tfbackend
    # See backend-remote.tfbackend.example for required values
  }
}

provider "azurerm" {
  features {}
}
