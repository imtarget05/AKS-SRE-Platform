variable "location" {
  type    = string
  default = "eastasia" # decided in ADR-012: SE-Asia SKUs subscription-blocked
}

variable "resource_group_name" {
  type    = string
  default = "rg-aks-platform-dev" # non-prod naming per approval
}

variable "cluster_name" {
  type    = string
  default = "aks-portfolio-dev"
}

variable "kubernetes_version" {
  type        = string
  default     = "1.36" # minor pin only; exact patch comes from AKS at create
  description = "AKS minor version from the live eastasia version query (1.36 GA)."
}

variable "system_pool_vm_size" {
  type        = string
  default     = "Standard_D4as_v5" # cheapest live 4-vCPU SKU, unrestricted in eastasia
  description = "System pool SKU: must satisfy ≥ 4 vCPU / 4 GB (docs minimum)."
}

variable "system_pool_node_count" {
  type        = number
  default     = 2
  description = "Docs minimum for a single-system-pool cluster."
}

# CRITICAL USER-POOL SAFETY: the temporary user pool must NOT exist at first
# apply (quota would sit at 10/10 immediately). Enable only after the
# system-only cluster is verified, run the placement + pull tests, then flip
# back to false and let the pool be destroyed in the same session.
variable "enable_workload_pool" {
  type        = bool
  default     = false
  description = "Temporary user pool for the 7A placement/ACR-pull proof."
}

variable "workload_pool_vm_size" {
  type        = string
  default     = "Standard_D2as_v5"
  description = "Temporary user pool SKU (2 vCPU; a different SKU hedges capacity)."
}

variable "workload_identity_client_id" {
  type        = string
  default     = ""
  description = "Set from a later phase: reserved for the future ACR-pull/workload identity wiring. Empty = skip federated wiring here."
}
