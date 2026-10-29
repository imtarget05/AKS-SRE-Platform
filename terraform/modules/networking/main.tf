resource "azurerm_resource_group" "networking" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = var.environment
    owner       = "student"
    purpose     = "platform-networking"
  }
}

resource "azurerm_virtual_network" "vnet" {
  name                = var.vnet_name
  location            = azurerm_resource_group.networking.location
  resource_group_name = azurerm_resource_group.networking.name
  address_space       = var.vnet_address_space

  tags = {
    environment = var.environment
  }
}

resource "azurerm_subnet" "apps" {
  name                 = "snet-apps"
  resource_group_name  = azurerm_resource_group.networking.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.subnet_apps_prefix]

  tags = {
    environment = var.environment
  }
}

resource "azurerm_subnet" "monitoring" {
  name                 = "snet-monitoring"
  resource_group_name  = azurerm_resource_group.networking.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.subnet_monitoring_prefix]

  tags = {
    environment = var.environment
  }
}

resource "azurerm_subnet" "private_endpoint" {
  name                 = "snet-private-endpoint"
  resource_group_name  = azurerm_resource_group.networking.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.subnet_private_endpoint_prefix]
  private_endpoint_network_policies = "Enabled"
  private_service_endpoint_network_policies = "Enabled"

  tags = {
    environment = var.environment
  }
}

resource "azurerm_network_security_group" "nsg" {
  name                = var.nsg_name
  location            = azurerm_resource_group.networking.location
  resource_group_name = azurerm_resource_group.networking.name

  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
    description                = "Deny all inbound traffic by default"
  }

  security_rule {
    name                       = "deny-all-outbound"
    priority                   = 200
    direction                  = "Outbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
    description                = "Deny all outbound traffic by default"
  }

  tags = {
    environment = var.environment
  }
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
  resource_group_name = azurerm_resource_group.networking.name

  tags = {
    environment = var.environment
  }
}

resource "azurerm_private_dns_zone_virtual_network_link" "link" {
  name                = "dnslink-${azurerm_virtual_network.vnet.name}"
  resource_group_name = azurerm_resource_group.networking.name
  private_dns_zone_name = azurerm_private_dns_zone.dns.name
  virtual_network_id  = azurerm_virtual_network.vnet.id
  registration_enabled = false

  tags = {
    environment = var.environment
  }
}

resource "azurerm_storage_account" "flow_logs" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.networking.name
  location                 = azurerm_resource_group.networking.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = {
    environment = var.environment
  }
}

resource "azurerm_network_watcher" "watcher" {
  name                = "nw-${var.resource_group_name}"
  location            = azurerm_resource_group.networking.location
  resource_group_name = azurerm_resource_group.networking.name

  tags = {
    environment = var.environment
  }
}

resource "azurerm_network_watcher_flow_log" "deny_events" {
  name                   = "flowlog-deny-events"
  location               = azurerm_resource_group.networking.location
  resource_group_name    = azurerm_resource_group.networking.name
  network_watcher_name   = azurerm_network_watcher.watcher.name
  target_resource_id     = azurerm_network_security_group.nsg.id
  storage_account_id     = azurerm_storage_account.flow_logs.id
  retention_policy {
    enabled = true
    days    = var.flow_log_retention_days
  }
  format {
    type = "JSON"
  }

  tags = {
    environment = var.environment
  }
}
