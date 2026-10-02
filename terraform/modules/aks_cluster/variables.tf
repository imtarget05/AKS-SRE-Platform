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
  default = 1
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

variable "environment" {
  type    = string
  default = "validation"
}
