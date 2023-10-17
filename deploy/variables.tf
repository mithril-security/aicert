variable "resource_group_location" {
  type        = string
  default     = "westeurope"
  description = "Location of the resource group."
}

variable "resource_group_name_prefix" {
  type        = string
  default     = "aicert_builder"
  description = "Prefix of the resource group name that's combined with a random ID so name is unique in your Azure subscription."
}

variable "instance_type" {
  type        = string
  default     = "Standard_DS1_v2"
  description = "Type/Size of VM to create."
}

variable "platform" {
  type        = string
  default     = "azure-tpm"
  description = "CSP and platform."
}