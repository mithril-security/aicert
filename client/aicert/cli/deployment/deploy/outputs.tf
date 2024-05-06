output "resource_group_name" {
  value = data.azurerm_resource_group.rg.name
}

output "public_ip_address" {
  value = azurerm_linux_virtual_machine.my_terraform_vm.public_ip_address
}

output "tls_private_key" {
  value     = tls_private_key.example_ssh.private_key_pem
  sensitive = true
}

output "storage_account_name" {
  value = data.azurerm_storage_account.model_storage.name
}

output "storage_container_name" {
  value = data.azurerm_storage_container.model_container.name
}