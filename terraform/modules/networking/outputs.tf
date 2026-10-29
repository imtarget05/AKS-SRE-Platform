output "resource_group_name" {
  value = azurerm_resource_group.networking.name
}

output "resource_group_id" {
  value = azurerm_resource_group.networking.id
}

output "vnet_id" {
  value = azurerm_virtual_network.vnet.id
}

output "vnet_name" {
  value = azurerm_virtual_network.vnet.name
}

output "subnet_apps_id" {
  value = azurerm_subnet.apps.id
}

output "subnet_monitoring_id" {
  value = azurerm_subnet.monitoring.id
}

output "subnet_private_endpoint_id" {
  value = azurerm_subnet.private_endpoint.id
}

output "nsg_id" {
  value = azurerm_network_security_group.nsg.id
}

output "nsg_name" {
  value = azurerm_network_security_group.nsg.name
}

output "private_dns_zone_id" {
  value = azurerm_private_dns_zone.dns.id
}

output "private_dns_zone_name" {
  value = azurerm_private_dns_zone.dns.name
}

output "flow_log_id" {
  value = azurerm_network_watcher_flow_log.deny_events.id
}
