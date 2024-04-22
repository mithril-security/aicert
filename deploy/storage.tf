terraform {
  required_providers {
    azurerm = {
        source = "hashicorp/azurerm"
    }
  }
}

provider "azurerm" {
  features {
    
  }
}

# TODO: {ResourceGroup} must be changed
resource "azurerm_resource_group" "{ResourceGroup}" {
  name      = "{ResourceGroup}"
  location  = variables.resource_group_location
}


# TODO: {StorageAccount} must be changed 

resource "azurerm_storage_account" "{StorageAccount}" {
    name                        = "{StorageAccount}"
    resource_group_name         = azurerm_resource_group.{ResourceGroup}.name
    location                    = azurerm_resource_group.{ResourceGroup}.location
    account_tier                = "Standard"
    account_replication_type    = "LRS"
}

resource "azurerm_storage_container" "{Blob}" {
    name                    = "{Blob}"
    storage_account_name    = azurerm_storage_account.{StorageAccount}.name
    container_access_type   = "private"
}

resource "azurerm_storage_queue" "{Queue}" {
    name                    = "{Queue}"
    storage_account_name    = azurerm_storage_container.{StorageAccount}.name
}

