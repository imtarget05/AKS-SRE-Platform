mock_provider "azurerm" {}

override_resource {
  target          = azurerm_network_security_group.nsg
  override_during = plan

  values = {
    id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/test-rg/providers/Microsoft.Network/networkSecurityGroups/test-nsg"
  }
}

run "verify_vnet_and_subnets" {
  command = plan

  assert {
    condition     = azurerm_virtual_network.vnet.name == var.vnet_name
    error_message = "VNet must exist"
  }

  assert {
    condition     = toset(azurerm_virtual_network.vnet.address_space) == toset(var.vnet_address_space)
    error_message = "VNet address space must match declared prefix"
  }

  assert {
    condition     = azurerm_subnet.apps.name == "snet-apps"
    error_message = "Apps subnet must exist"
  }

  assert {
    condition     = azurerm_subnet.monitoring.name == "snet-monitoring"
    error_message = "Monitoring subnet must exist"
  }

  assert {
    condition     = azurerm_subnet.private_endpoint.name == "snet-private-endpoint"
    error_message = "Private endpoint subnet must exist"
  }
}

run "verify_nsg_deny_default" {
  command = plan

  assert {
    condition     = azurerm_network_security_group.nsg.name == var.nsg_name
    error_message = "NSG must exist"
  }

  assert {
    condition     = azurerm_network_security_rule.deny_all_inbound.access == "Deny"
    error_message = "NSG inbound default rule must deny"
  }

  assert {
    condition     = azurerm_network_security_rule.deny_all_outbound.access == "Deny"
    error_message = "NSG outbound default rule must deny"
  }
}

run "verify_private_dns_zone_delegation" {
  command = plan

  assert {
    condition     = azurerm_private_dns_zone.dns.name == var.private_dns_zone_name
    error_message = "Private DNS zone must exist"
  }

  assert {
    condition     = azurerm_private_dns_zone_virtual_network_link.link.name == "dnslink-${var.vnet_name}"
    error_message = "Private DNS zone virtual network link must exist"
  }

  assert {
    condition     = azurerm_private_dns_zone_virtual_network_link.link.registration_enabled == false
    error_message = "Private DNS zone virtual network link must disable registration"
  }

}

run "verify_deny_event_evidence" {
  command = plan

  assert {
    condition     = azurerm_network_watcher_flow_log.deny_events.name == "flowlog-deny-events"
    error_message = "Network Watcher flow log must exist for deny-event evidence"
  }

  assert {
    condition     = azurerm_network_watcher_flow_log.deny_events.enabled == true
    error_message = "Network Watcher flow log must be enabled"
  }

  assert {
    condition     = azurerm_network_watcher_flow_log.deny_events.retention_policy[0].enabled == true
    error_message = "Flow log retention must be enabled"
  }

  assert {
    condition     = azurerm_network_watcher_flow_log.deny_events.target_resource_id == azurerm_network_security_group.nsg.id
    error_message = "Flow log must target the deny NSG"
  }

  assert {
    condition     = azurerm_storage_account.flow_logs.network_rules[0].default_action == "Deny"
    error_message = "Flow-log storage must deny public network access by default"
  }

  assert {
    condition     = contains(azurerm_storage_account.flow_logs.network_rules[0].bypass, "AzureServices")
    error_message = "Flow-log storage must allow trusted Azure services"
  }
}
