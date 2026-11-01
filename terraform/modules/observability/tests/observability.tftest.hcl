mock_provider "azurerm" {}
mock_provider "kubernetes" {}
mock_provider "helm" {}

run "verify_log_analytics_workspace" {
  command = plan

  variables {
    cluster_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test-rg/providers/Microsoft.ContainerService/managedClusters/test-aks"
  }

  assert {
    condition     = azurerm_log_analytics_workspace.workspace.name == var.log_analytics_workspace_name
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

  variables {
    cluster_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test-rg/providers/Microsoft.ContainerService/managedClusters/test-aks"
  }

  assert {
    condition     = azurerm_monitor_data_collection_rule.dcr.name == var.data_collection_rule_name
    error_message = "Data Collection Rule must exist"
  }

  assert {
    condition     = length(azurerm_monitor_data_collection_rule.dcr.destinations) == 1
    error_message = "DCR must have a Log Analytics destination"
  }

  assert {
    condition     = azurerm_monitor_data_collection_rule.dcr.destinations[0].log_analytics[0].name == "la-destination"
    error_message = "DCR destination must name the Log Analytics workspace destination"
  }

  assert {
    condition     = contains(azurerm_monitor_data_collection_rule.dcr.data_flow[0].destinations, "la-destination")
    error_message = "DCR data flow must route to the Log Analytics destination"
  }

  assert {
    condition     = contains(azurerm_monitor_data_collection_rule.dcr.data_sources[0].platform_telemetry[0].streams, "Microsoft-InsightsMetrics")
    error_message = "DCR must collect InsightsMetrics platform telemetry"
  }

  assert {
    condition     = azurerm_monitor_data_collection_rule_association.aks_cluster.target_resource_id == var.cluster_id
    error_message = "DCR must be associated with the AKS cluster"
  }
}

run "verify_otel_collector_addon" {
  command = plan

  variables {
    cluster_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test-rg/providers/Microsoft.ContainerService/managedClusters/test-aks"
  }

  assert {
    condition     = kubernetes_manifest.otel_collector_namespace.manifest.metadata.name == var.otel_collector_namespace
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
