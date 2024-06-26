variable "resource_group_location" {
  type        = string
  default     = "eastus"
  description = "Location of the resource group."
}

variable "resource_group_name" {
  type        = string
  default     = "aicert_server"
  description = "Prefix of the resource group name that's combined with a random ID so name is unique in your Azure subscription."
}

variable "instance_type" {
  type        = string
  default     = "Standard_NC24ads_A100_v4"
  description = "Type/Size of VM to create."
}

variable "gallery_name" {
  type        = string
  default     = "aicert-gallery"
  description = "Name of the Image Gallery."
}

variable "storage_account" {
  type        = string
  default     = "aicertstorage"
  description = "Storage account name."
}

variable "storage_container" {
  type        = string
  default     = "aicertcontainer"
  description = "Storage account container name."
}