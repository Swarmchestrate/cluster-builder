terraform {
  required_providers {
    k3s = {
      source = "striveworks/k3s"
      version = "1.0.0"
    }
  }
}

# VARIABLES
variable "cluster_name" {}
variable "resource_name" {}
variable "k3s_role" {}

variable "edge_device_ip" {}
variable "cloud" {
  default = "edge"
}
variable "ssh_user" {}
variable "ssh_key" {}
variable "ssh_auth_method" {}
variable "ssh_port" {
  default = 22
}

variable "k3s_token" {}

variable "master_ip" {
  default = null
}

variable "ha" {
  default = false
}

# VALIDATION 
locals {
  use_key_auth = var.ssh_auth_method == "key" && var.ssh_key != ""
}

resource "null_resource" "validate_auth" {
  count = local.use_key_auth ? 0 : 1

  provisioner "local-exec" {
    command = "echo 'ERROR: ssh_auth_method must be key and ssh_key must be set' && exit 1"
  }
}

# K3S SERVER (Standalone)
resource "k3s_server" "k3s" {
  count = (var.k3s_role == "master" && !var.ha) ? 1 : 0

  auth = {
    host        = var.edge_device_ip
    user        = var.ssh_user
    private_key_file = var.ssh_key
    port        = var.ssh_port
  }

  bootstrap_token = var.k3s_token

  config = <<-EOT
    node-name: ${var.resource_name}
    node-label: labels.swarmchestrate.eu/ms_id=${var.resource_name}
    cluster-name: ${var.cluster_name}
  EOT
}


# HA INIT
resource "k3s_server" "k3s_ha_init" {
  count = (var.k3s_role == "master" && var.ha) ? 1 : 0

  auth = {
    host        = var.edge_device_ip
    user        = var.ssh_user
    private_key_file = var.ssh_key
    port        = var.ssh_port
  }

  bootstrap_token = var.k3s_token

  config = <<-EOT
    node-name: ${var.resource_name}
    node-label: labels.swarmchestrate.eu/ms_id=${var.resource_name}
    cluster-name: ${var.cluster_name}
  EOT

  highly_available = {
    cluster_init = true
  }
}

# HA JOIN
resource "k3s_server" "k3s_ha_join" {
  count = var.k3s_role == "ha" ? 1 : 0

  auth = {
    host        = var.edge_device_ip
    user        = var.ssh_user
    private_key_file = var.ssh_key
    port        = var.ssh_port
  }

  config = <<-EOT
    node-name: ${var.resource_name}
    node-label: labels.swarmchestrate.eu/ms_id=${var.resource_name}
  EOT

  highly_available = {
    cluster_init = false
    server       = "https://${var.master_ip}:6443"
    token        = var.k3s_token
  }
}

# WORKER
resource "k3s_agent" "k3s" {
  count = var.k3s_role == "worker" ? 1 : 0

  auth = {
    host        = var.edge_device_ip
    user        = var.ssh_user
    private_key_file = var.ssh_key
    port        = var.ssh_port
  }

  server = "https://${var.master_ip}:6443"
  token  = var.k3s_token

  config = <<-EOT
    node-name: ${var.resource_name}
    node-label: labels.swarmchestrate.eu/ms_id=${var.resource_name}
  EOT
  
}

output "cluster_name" {
  value = var.cluster_name
}

output "k3s_role" {
  value = var.k3s_role
}

output "resource_name" {
  value = var.resource_name
}

output "edge_device_ip" {
  value = var.edge_device_ip
}


output "master_ip" {
  value = var.k3s_role == "master" ? var.edge_device_ip : var.master_ip
}

output "worker_ip" {
  value = var.k3s_role == "worker" ? var.edge_device_ip : null
}

output "ha_ip" {
  value = var.k3s_role == "ha" ? var.edge_device_ip : null
}

output "k3s_token" {
  value = var.k3s_token
}