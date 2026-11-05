variable "location" {
  type    = string
  default = "eastasia"
}

variable "resource_group_name" {
  type    = string
  default = "rg-aks-platform-dev"
}

variable "cluster_name" {
  type    = string
  default = "aks-portfolio-dev"
}

variable "dns_prefix" {
  type    = string
  default = "aksportfoliodev"
}

variable "kubernetes_version" {
  type    = string
  default = "1.36"
}

variable "system_pool_vm_size" {
  type    = string
  default = "Standard_D2s_v6"
}

variable "system_pool_node_count" {
  type    = number
  default = 2
  # Sacombank budget #1 confirmed: prod requires >= 2 nodes across zones for HA
}

variable "enable_workload_pool" {
  type    = bool
  default = true
}

variable "workload_pool_vm_size" {
  type    = string
  default = "Standard_D2s_v6"
}

variable "workload_pool_node_count" {
  type    = number
  default = 1
}

variable "workload_pool_autoscaling" {
  description = "Opt-in AKS cluster autoscaler for the D2s_v6 user pool; at most three user nodes plus one fixed system node stay within the 10-vCPU validation envelope."
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

variable "environment" {
  type    = string
  default = "validation"
}

variable "sku_tier" {
  type    = string
  default = "Standard"
}

variable "private_cluster_enabled" {
  description = "Public AKS API is the safe default for local validation and GitOps verification. Private clusters must be opted in explicitly only when the environment has private DNS/VNet reachability and the owner accepts the read-only lockout risk."
  type        = bool
  default     = false
}

variable "zones" {
  type    = list(string)
  default = ["1", "2", "3"]
}
