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

variable "log_analytics_workspace_name" {
  type    = string
  default = "law-aks-platform"
}

variable "retention_in_days" {
  type    = number
  default = 30
}

variable "data_collection_rule_name" {
  type    = string
  default = "dcr-aks-platform"
}

variable "cluster_id" {
  type    = string
}

variable "otel_collector_namespace" {
  type    = string
  default = "otel-collector"
}

variable "otel_collector_repository" {
  type    = string
  default = "https://open-telemetry.github.io/opentelemetry-helm-charts"
}

variable "otel_collector_chart" {
  type    = string
  default = "opentelemetry-collector"
}

variable "otel_collector_version" {
  type    = string
  default = "0.100.0"
}
