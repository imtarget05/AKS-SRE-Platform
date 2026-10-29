mock_provider "azurerm" {}

run "verify_vnet_and_subnets" {
  command = plan

  assert {
    condition     = length(azurerm_virtual_network.vnet) == 1
    error_message = "VNet must exist"
  }

  assert {
    condition     = azurerm_virtual_network.vnet.address_space == var.vnet_address_space
    error_message = "VNet address space must match declared prefix"
  }

  assert {
    condition     = length(azurerm_subnet.apps) == 1
    error_message = "Apps subnet must exist"
  }

  assert {
    condition     = length(azurerm_subnet.monitoring) == 1
    error_message = "Monitoring subnet must exist"
  }

  assert {
    condition     = length(azurerm_subnet.private_endpoint) == 1
    error_message = "Private endpoint subnet must exist"
  }
}

run "verify_nsg_deny_default" {
  command = plan

  assert {
    condition     = length(azurerm_network_security_group.nsg) == 1
    error_message = "NSG must exist"
  }

  assert {
    condition     = azurerm_network_security_group.nsg.security_rule[0].access == "Deny"
    error_message = "NSG inbound default rule must deny"
  }

  assert {
    condition     = azurerm_network_security_group.nsg.security_rule[1].access == "Deny"
    error_message = "NSG outbound default rule must deny"
  }
}

run "verify_private_dns_zone_delegation" {
  command = plan

  assert {
    condition     = length(azurerm_private_dns_zone.dns) == 1
    error_message = "Private DNS zone must exist"
  }

  assert {
    condition     = length(azurerm_private_dns_zone_virtual_network_link.link) == 1
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
    condition     = length(azurerm_network_watcher_flow_log.deny_events) == 1
    error_message = "Network Watcher flow log must exist for deny-event evidence"
  }

  assert {
    condition     = azurerm_network_watcher_flow_log.deny_events.retention_policy[0].enabled == true
    error_message = "Flow log retention must be enabled"
  }

  assert {
    condition     = azurerm_network_watcher_flow_log.deny_events.target_resource_id == azurerm_network_security_group.nsg.id
    error_message = "Flow log must target the deny NSG"
  }
}
