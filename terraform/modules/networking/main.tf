resource "azurerm_virtual_network" "vnet" {
  name                = var.vnet_name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.vnet_address_space

  tags = {
    environment = var.environment
    owner       = "student"
    purpose     = "platform-networking"
  }
}

resource "azurerm_subnet" "apps" {
  name                 = "snet-apps"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.subnet_apps_prefix]
}

resource "azurerm_subnet" "monitoring" {
  name                 = "snet-monitoring"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.subnet_monitoring_prefix]
}

resource "azurerm_subnet" "private_endpoint" {
  name                                          = "snet-private-endpoint"
  resource_group_name                           = var.resource_group_name
  virtual_network_name                          = azurerm_virtual_network.vnet.name
  address_prefixes                              = [var.subnet_private_endpoint_prefix]
  private_endpoint_network_policies             = "Enabled"
  private_link_service_network_policies_enabled = true
}

resource "azurerm_network_security_group" "nsg" {
  name                = var.nsg_name
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = {
    environment = var.environment
    owner       = "student"
    purpose     = "platform-networking"
  }
}

resource "azurerm_network_security_rule" "deny_all_inbound" {
  name                        = "deny-all-inbound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.nsg.name
  description                 = "Deny all inbound traffic by default"
}

resource "azurerm_network_security_rule" "deny_all_outbound" {
  name                        = "deny-all-outbound"
  priority                    = 200
  direction                   = "Outbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.nsg.name
  description                 = "Deny all outbound traffic by default"
}

resource "azurerm_subnet_network_security_group_association" "apps" {
  subnet_id                 = azurerm_subnet.apps.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_subnet_network_security_group_association" "monitoring" {
  subnet_id                 = azurerm_subnet.monitoring.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_subnet_network_security_group_association" "private_endpoint" {
  subnet_id                 = azurerm_subnet.private_endpoint.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_private_dns_zone" "dns" {
  name                = var.private_dns_zone_name
  resource_group_name = var.resource_group_name

  tags = {
    environment = var.environment
    owner       = "student"
    purpose     = "platform-networking"
  }
}

resource "azurerm_private_dns_zone_virtual_network_link" "link" {
  name                 = "dnslink-${azurerm_virtual_network.vnet.name}"
  private_dns_zone_id  = azurerm_private_dns_zone.dns.id
  virtual_network_id   = azurerm_virtual_network.vnet.id
  registration_enabled = false

  tags = {
    environment = var.environment
    owner       = "student"
    purpose     = "platform-networking"
  }
}
