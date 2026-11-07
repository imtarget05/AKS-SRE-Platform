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

variable "sku_tier" {
  type        = string
  default     = "Free"
  description = "AKS management tier; Free is sufficient for temporary validation."
}

variable "system_pool_vm_size" {
  type        = string
  default     = "Standard_D2s_v6" # Sized for 10 vCPU quota envelope (ADR-014)
  description = "System pool SKU (2 vCPU; leaves room for user pool within 10 vCPU quota)."
}

variable "system_pool_node_count" {
  type        = number
  default     = 2
  description = "System pool node count for HA foundation (requires >= 2 nodes)."
}

variable "enable_workload_pool" {
  type        = bool
  default     = true
  description = "Temporary user pool for placement/workload proof."
}

variable "workload_pool_vm_size" {
  type        = string
  default     = "Standard_D2s_v6"
  description = "User pool SKU."
}

variable "workload_pool_autoscaling" {
  description = "Opt-in bounded cluster autoscaler for the user pool. The default keeps the existing fixed-size behavior."
  type = object({
    enabled   = bool
    min_nodes = number
    max_nodes = number
  })
  default = {
    enabled   = false
    min_nodes = 1
    max_nodes = 3
  }

  validation {
    condition = (
      var.workload_pool_autoscaling.min_nodes >= 1 &&
      var.workload_pool_autoscaling.min_nodes <= var.workload_pool_autoscaling.max_nodes &&
      var.workload_pool_autoscaling.max_nodes <= 3 &&
      floor(var.workload_pool_autoscaling.min_nodes) == var.workload_pool_autoscaling.min_nodes &&
      floor(var.workload_pool_autoscaling.max_nodes) == var.workload_pool_autoscaling.max_nodes
    )
    error_message = "User pool autoscaling requires integer min/max nodes with 1 <= min <= max <= 3."
  }
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

variable "vnet_name" {
  type        = string
  default     = "aks-sre-vnet"
  description = "VNet name for the AKS platform network."
}

variable "vnet_address_space" {
  type        = list(string)
  default     = ["10.0.0.0/16"]
  description = "VNet address space."
}

variable "subnet_apps_prefix" {
  type        = string
  default     = "10.0.1.0/24"
  description = "AKS subnet prefix."
}

variable "subnet_monitoring_prefix" {
  type        = string
  default     = "10.0.2.0/24"
  description = "App Gateway / monitoring subnet prefix."
}

variable "subnet_private_endpoint_prefix" {
  type        = string
  default     = "10.0.3.0/24"
  description = "PaaS private endpoint subnet prefix."
}

variable "nsg_name" {
  type        = string
  default     = "nsg-aks-platform"
  description = "Network security group name."
}

variable "private_dns_zone_name" {
  type        = string
  default     = "privatelink.aksplatform.local"
  description = "Private DNS zone name for private endpoints."
}

variable "zones" {
  type        = list(string)
  default     = ["1", "2", "3"]
  description = "Availability zones for AKS system pool."
}

variable "environment" {
  type        = string
  default     = "validation"
  description = "Environment tag for all Azure resources."
}
