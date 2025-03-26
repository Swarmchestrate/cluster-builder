# variables.tf
variable "openstack_region" {}
variable "auth_url" {}
variable "application_credential_id" {}
variable "application_credential_secret" {}
variable "cluster_name" {}
variable "resource_name" {}
variable "k3s_role" {}
variable "master_ip" {
  default = null
}
variable "pg_conn_str" {}
variable "openstack_size" {}
variable "openstack_flavor_id" {}
variable "instance_type" {}
variable "ssh_key_name" {}
variable "k3s_token" {}
variable "cloud" {
  default = null
}
variable "ha" {
  default = null
}

# provider.tf
provider "openstack" {
  auth_url                     = var.auth_url
  application_credential_id     = var.application_credential_id
  application_credential_secret = var.application_credential_secret
  region                       = var.openstack_region
}

# Network common to all nodes
data "openstack_networking_network_v2" "cluster_network" {
  name = "default
}

# Block storage for each node role
resource "openstack_blockstorage_volume_v3" "k3s_node" {
  name        = "${var.cluster_name}-${var.resource_name}"
  size        = var.openstack_size
  volume_type = var.openstack_volume_type
  image_id    = "{{ image_id }}"
}

# Compute instance for each role
resource "openstack_compute_instance_v2" "k3s_node" {
  name            = "${var.cluster_name}-${var.resource_name}"
  flavor_id       = "var.openstack_flavor_id"
  key_pair        = "var.ssh_key_name
  security_groups = [openstack_networking_secgroup_v2.k3s_sg.name]

  block_device {
    source_type           = "image"
    uuid                  = var.instance_type
    destination_type      = "volume"
    volume_size           = var.openstack_size
    delete_on_termination = true
  }

  network {
    uuid = data.openstack_networking_network_v2.cluster_network.id
  }

  user_data = templatefile("${path.module}/${var.k3s_role}_user_data.sh.tpl", {
    ha           = var.ha,
    k3s_token    = var.k3s_token,
    master_ip    = var.master_ip,
    cluster_name = var.cluster_name
    }
  )

  tags = {
    Name        = "${var.cluster_name}-${var.resource_name}"
    ClusterName = var.cluster_name
  }
}
resource "openstack_networking_secgroup_v2" "k3s_sg" {
  name        = "${var.k3s_role}-${var.cluster_name}-${var.resource_name}"  
  description = "Security group for K3s node in cluster ${var.cluster_name}"
  tags = {
      Name = "${var.k3s_role}-${var.cluster_name}-${var.resource_name}"
    }
}

# Security Group Rules
locals {
  ingress_rules = [
    { from = 2379, to = 2380, proto = "tcp", desc = "etcd communication" },
    { from = 6443, to = 6443, proto = "tcp", desc = "K3s API server" },
    { from = 8472, to = 8472, proto = "udp", desc = "VXLAN for Flannel" },
    { from = 10250, to = 10250, proto = "tcp", desc = "Kubelet metrics" },
    { from = 51820, to = 51820, proto = "udp", desc = "Wireguard IPv4" },
    { from = 51821, to = 51821, proto = "udp", desc = "Wireguard IPv6" },
    { from = 5001, to = 5001, proto = "tcp", desc = "Embedded registry" },
    { from = 22, to = 22, proto = "tcp", desc = "SSH access" },
    { from = 80, to = 80, proto = "tcp", desc = "HTTP access" },
    { from = 443, to = 443, proto = "tcp", desc = "HTTPS access" },
    { from = 53, to = 53, proto = "udp", desc = "DNS for CoreDNS" },
    { from = 5432, to = 5432, proto = "tcp", desc = "PostgreSQL access" }
  ]
}

resource "openstack_networking_secgroup_rule_v2" "k3s_rules" {
  count            = length(local.ingress_rules)
  direction        = "ingress"
  ethertype        = "IPv4"
  protocol         = local.ingress_rules[count.index].proto
  port_range_min   = local.ingress_rules[count.index].from
  port_range_max   = local.ingress_rules[count.index].to
  remote_ip_prefix = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.k3s_sg.id
}

# outputs.tf
output "cluster_name" {
  value = var.k3s_role == "master" ? var.cluster_name : null
}

output "master_ip" {
  value = var.k3s_role == "master" ? aws_instance.k3s_node.public_ip : null
}