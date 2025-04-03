provider "openstack" {
  auth_url                     = var.openstack_auth_url
  application_credential_id     = var.openstack_application_credential_id
  application_credential_secret = var.openstack_application_credential_secret
  region                       = var.openstack_region
}

variable "openstack_auth_url" {
  description = "Openstack secret key"
  type        = string
}

variable "openstack_application_credential_id" {
  description = "Openstack application application credential id"
  type        = string
  sensitive   = true
}

variable "openstack_application_credential_secret" {
  description = "Openstack application credential secret"
  type        = string
  sensitive   = true
}

variable "openstack_region" {
  description = "Openstack region for resources"
  type        = string
}