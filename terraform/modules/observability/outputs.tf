output "workspace_name" {
  value = azurerm_log_analytics_workspace.workspace.name
}

output "workspace_id" {
  value = azurerm_log_analytics_workspace.workspace.id
}

output "retention_in_days" {
  value = azurerm_log_analytics_workspace.workspace.retention_in_days
}

output "data_collection_rule_name" {
  value = azurerm_monitor_data_collection_rule.dcr.name
}

output "data_collection_rule_id" {
  value = azurerm_monitor_data_collection_rule.dcr.id
}

output "otel_collector_namespace" {
  value = var.otel_collector_namespace
}

output "otel_collector_release_name" {
  value = helm_release.otel_collector.name
}
