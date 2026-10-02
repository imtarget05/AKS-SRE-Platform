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
  default     = "Standard_D2s_v6" # Sized for 10 vCPU quota envelope (ADR-014)
  description = "System pool SKU (2 vCPU; leaves room for user pool within 10 vCPU quota)."
}

variable "system_pool_node_count" {
  type        = number
  default     = 1
  description = "System pool node count for transient validation."
}

variable "enable_workload_pool" {
  type        = bool
  default     = false
  description = "Temporary user pool for placement/workload proof."
}

variable "workload_pool_vm_size" {
  type        = string
  default     = "Standard_D2s_v6"
  description = "User pool SKU."
}

variable "enable_wi_proof" {
  type        = bool
  default     = false
  description = "Temporary Workload Identity proof identity."
}

variable "enable_acr_integration" {
  type        = bool
  default     = false
  description = "Gated ACR integration and AcrPull assignment."
}

variable "acr_name" {
  type        = string
  default     = "acrflashsalep6"
  description = "Target ACR name for role assignment."
}

variable "acr_resource_group_name" {
  type        = string
  default     = "rg-flashsale-release"
  description = "Target ACR resource group."
}
