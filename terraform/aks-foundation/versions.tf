# Phase 7A — AKS Foundation root (CLOUD FOUNDATION ONLY).
# Approved scope: eastasia, aks-portfolio-dev in rg-aks-platform-dev,
# system pool 2× D4s_v6 (min docs requirement; D4as_v5 BLOCKED 2026-09-21, DASv5 quota 0),
# OPTIONAL temporary user pool D2s_v6 gated by enable_workload_pool (default false).
# NOT owned here: Helm releases, KEDA, apps, ingress, ArgoCD, monitoring.
terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
  }

  # Remote encrypted state on the portfolio tfstate account (same pattern as
  # the backup-storage and release roots). Dedicated key — never mixed with
  # application-backup state or Terraform cloud defaults.
  backend "azurerm" {
    resource_group_name  = "rg-flashsale-tfstate"
    storage_account_name = "stflashs3ctfbk01"
    container_name       = "tfstate"
    key                  = "aks-foundation.terraform.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  features {}
}
