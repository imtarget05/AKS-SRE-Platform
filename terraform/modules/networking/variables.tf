variable "location" {
  type    = string
  default = "eastasia"
}

variable "resource_group_name" {
  type    = string
  default = "rg-aks-platform-dev"
}

variable "environment" {
  type    = string
  default = "validation"
}

variable "vnet_name" {
  type    = string
  default = "vnet-aks-platform"
}

variable "vnet_address_space" {
  type    = list(string)
  default = ["10.0.0.0/16"]
}

variable "subnet_apps_prefix" {
  type    = string
  default = "10.0.1.0/24"
}

variable "subnet_monitoring_prefix" {
  type    = string
  default = "10.0.2.0/24"
}

variable "subnet_private_endpoint_prefix" {
  type    = string
  default = "10.0.3.0/24"
}

variable "nsg_name" {
  type    = string
  default = "nsg-aks-platform"
}

variable "private_dns_zone_name" {
  type    = string
  default = "privatelink.aksplatform.local"
}

variable "storage_account_name" {
  type    = string
  default = "sakplatformlogs"
}

variable "flow_log_retention_days" {
  type    = number
  default = 30
}
