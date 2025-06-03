variable "openstack_auth_method" {
  description = "Auth method: 'appcreds' or 'userpass'"
  type        = string
  default     = "appcreds"
}

variable "openstack_auth_url" {
  description = "Openstack secret key"
  type        = string
}

variable "openstack_region" {
  description = "Openstack region for resources"
  type        = string
}

# AppCred variables
variable "openstack_application_credential_id" {
  description = "Openstack application application credential id"
  type        = string
  sensitive   = true
  default = ""
}

variable "openstack_application_credential_secret" {
  description = "Openstack application credential secret"
  type        = string
  sensitive   = true
  default = ""
}

# Username/password variables
variable "openstack_user_name" {
  description = "Username for OpenStack (if not using appcred)"
  type        = string
  default = ""
}

variable "openstack_password" {
  description = "Password for OpenStack user"
  type        = string
  sensitive   = true
  default = ""
}

variable "openstack_project_id" {
  description = "Project ID to use with OpenStack"
  type        = string
  default = ""
}

variable "openstack_user_domain_name" {
  description = "User domain name"
  type        = string
  default = ""
}

# Dynamic provider config (manually switching fields)
provider "openstack" {
  auth_url = var.openstack_auth_url
  region   = var.openstack_region

  application_credential_id     = var.openstack_auth_method == "appcreds" ? var.openstack_application_credential_id : null
  application_credential_secret = var.openstack_auth_method == "appcreds" ? var.openstack_application_credential_secret : null

  user_name        = var.openstack_auth_method == "userpass" ? var.openstack_user_name : null
  password         = var.openstack_auth_method == "userpass" ? var.openstack_password : null
  tenant_id       = var.openstack_auth_method == "userpass" ? var.openstack_project_id : null
  user_domain_name = var.openstack_auth_method == "userpass" ? var.openstack_user_domain_name : null
}
