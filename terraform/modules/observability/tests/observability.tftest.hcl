mock_provider "azurerm" {}
mock_provider "kubernetes" {}
mock_provider "helm" {}

run "verify_log_analytics_workspace" {
  command = plan

  assert {
    condition     = length(azurerm_log_analytics_workspace.workspace) == 1
    error_message = "Log Analytics workspace must exist"
  }

  assert {
    condition     = azurerm_log_analytics_workspace.workspace.sku == "PerGB2018"
    error_message = "Log Analytics workspace must use PerGB2018 SKU"
  }

  assert {
    condition     = azurerm_log_analytics_workspace.workspace.retention_in_days >= 30
    error_message = "Log Analytics retention must be at least 30 days"
  }
}

run "verify_data_collection_rule" {
  command = plan

  assert {
    condition     = length(azurerm_monitor_data_collection_rule.dcr) == 1
    error_message = "Data Collection Rule must exist"
  }

  assert {
    condition     = length(azurerm_monitor_data_collection_rule.dcr.destination) == 1
    error_message = "DCR must have a Log Analytics destination"
  }

  assert {
    condition     = azurerm_monitor_data_collection_rule.dcr.destination[0].log_analytics[0].workspace_resource_id == azurerm_log_analytics_workspace.workspace.id
    error_message = "DCR destination must point at the Log Analytics workspace"
  }
}

run "verify_otel_collector_addon" {
  command = plan

  assert {
    condition     = length(kubernetes_manifest.otel_collector_namespace) == 1
    error_message = "OTel Collector namespace must exist"
  }

  assert {
    condition     = helm_release.otel_collector.name == "otel-collector"
    error_message = "OTel Collector Helm release must be named otel-collector"
  }

  assert {
    condition     = helm_release.otel_collector.namespace == var.otel_collector_namespace
    error_message = "OTel Collector must deploy into the declared namespace"
  }
}
