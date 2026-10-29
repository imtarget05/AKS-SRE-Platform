resource "azurerm_resource_group" "observability" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = var.environment
    owner       = "student"
    purpose     = "platform-observability"
  }
}

resource "azurerm_log_analytics_workspace" "workspace" {
  name                = var.log_analytics_workspace_name
  location            = azurerm_resource_group.observability.location
  resource_group_name = azurerm_resource_group.observability.name
  sku                 = "PerGB2018"
  retention_in_days   = var.retention_in_days

  tags = {
    environment = var.environment
  }
}

resource "azurerm_monitor_data_collection_rule" "dcr" {
  name                = var.data_collection_rule_name
  location            = azurerm_resource_group.observability.location
  resource_group_name = azurerm_resource_group.observability.name

  data_source {
    kind = "InsightsMetrics"
  }

  data_flow {
    destinations    = [azurerm_log_analytics_workspace.workspace.name]
    streams         = ["Microsoft-InsightsMetrics"]
    output_stream   = "Microsoft-InsightsMetrics"
  }

  destination {
    log_analytics {
      workspace_resource_id = azurerm_log_analytics_workspace.workspace.id
      name                  = "la-destination"
    }
  }

  tags = {
    environment = var.environment
  }
}

resource "kubernetes_manifest" "otel_collector_namespace" {
  manifest = {
    apiVersion = "v1"
    kind       = "Namespace"
    metadata = {
      name = var.otel_collector_namespace
    }
  }
}

resource "helm_release" "otel_collector" {
  name       = "otel-collector"
  repository = var.otel_collector_repository
  chart      = var.otel_collector_chart
  version    = var.otel_collector_version
  namespace  = kubernetes_manifest.otel_collector_namespace.metadata[0].name

  set {
    name  = "logs.endpoint"
    value = azurerm_log_analytics_workspace.workspace.id
  }

  depends_on = [
    kubernetes_manifest.otel_collector_namespace,
  ]
}
