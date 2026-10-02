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

  # Remote encrypted state — PARTIAL CONFIG, values supplied per environment.
  #
  # HISTORY, because it explains why this block is empty rather than a copy of
  # what used to be here. This block previously carried hardcoded values:
  #
  #     resource_group_name  = "rg-flashsale-tfstate"
  #     storage_account_name = "stflashs3ctfbk01"
  #     container_name       = "tfstate"
  #     key                  = "aks-foundation.terraform.tfstate"
  #
  # Those pointed at ANOTHER repository's state store (FlashSale-Backend), and
  # that storage account is gone from this subscription. `terraform init` failed
  # with "no such host" — which is at least fail-closed, since it did NOT fall
  # back to local state, but it made this root un-initialisable and un-deployable.
  #
  # Two rules are now enforced instead:
  #
  #   1. NO CROSS-REPO STATE COUPLING. This repository owns its own state
  #      identity (rg-aks-tfstate / staksstate / tfstate). It must never be
  #      initialised against another project's storage account, and it never
  #      reads or writes another project's state keys. tests/probe_backend_isolation.py
  #      fails the build if any forbidden portfolio resource name appears here.
  #
  #   2. NO CREDENTIALS IN SOURCE. Partial config means no value, key or token
  #      is committed; environments/<env>/backend.hcl carries only storage
  #      identity and key.
  #
  # `use_azuread_auth = true` lives in the backend.hcl files, not here, because
  # authentication is per-environment (see S7 below). `use_oidc` is deliberately
  # NOT set anywhere in committed config: a static value forces the GitHub
  # Actions OIDC path, which reads ACTIONS_ID_TOKEN_REQUEST_TOKEN and therefore
  # breaks a local `az login` init. One config, two paths:
  #
  #   local : `az login` supplies the token
  #   CI    : ARM_USE_OIDC=true ARM_USE_AZUREAD_AUTH=true ARM_CLIENT_ID=…
  #           ARM_TENANT_ID=… ARM_SUBSCRIPTION_ID=…
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
}
