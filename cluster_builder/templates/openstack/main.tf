# variables.tf
variable "cluster_name" {}
variable "resource_name" {}
variable "k3s_role" {}
variable "master_ip" {
  default = null
}
variable "openstack_size" {}
variable "openstack_volume_type" {}
variable "openstack_image_id" {}
variable "openstack_flavor_id" {}
variable "ssh_key_name" {}
variable "k3s_token" {}
variable "cloud" {
  default = null
}
variable "ha" {
  default = null
}

# Network common to all nodes
data "openstack_networking_network_v2" "cluster_network" {
  name = "default"
}

# Block storage for each node role
resource "openstack_blockstorage_volume_v3" "root_volume" {
  name        = "${var.cluster_name}-${var.resource_name}-volume"
  size        = var.openstack_size
  volume_type = var.openstack_volume_type
  image_id    = var.openstack_image_id
}

# Compute instance for each role
resource "openstack_compute_instance_v2" "k3s_node" {
  name             = "${var.cluster_name}-${var.resource_name}"
  flavor_name       = var.openstack_flavor_id
  key_pair        = var.ssh_key_name
  security_groups = [openstack_networking_secgroup_v2.k3s_sg.id]

  block_device {
    uuid                  = openstack_blockstorage_volume_v3.root_volume.id
    source_type           = "volume"
    destination_type      = "volume"
    boot_index            = 0
    delete_on_termination = true
  }

  network {
    uuid = data.openstack_networking_network_v2.cluster_network.id
  }

  user_data = templatefile(
    "${path.module}/${var.k3s_role}_user_data.sh.tpl",
    {
      ha            = var.ha,
      k3s_token     = var.k3s_token,
      master_ip     = var.master_ip,
      cluster_name  = var.cluster_name
    }
  )

   tags = [
    "${var.cluster_name}-${var.resource_name}",
    "ClusterName=${var.cluster_name}",
    "Role=${var.k3s_role}"
  ]
}

# Define a local variable for the security group rules
locals {
  ingress_rules = [
    { from = 2379, to = 2380, proto = "tcp", desc = "etcd communication", roles = ["master", "ha"] },
    { from = 6443, to = 6443, proto = "tcp", desc = "K3s API server", roles = ["master", "ha", "worker"] },
    { from = 8472, to = 8472, proto = "udp", desc = "VXLAN for Flannel", roles = ["master", "ha", "worker"] },
    { from = 10250, to = 10250, proto = "tcp", desc = "Kubelet metrics", roles = ["master", "ha", "worker"] },
    { from = 51820, to = 51820, proto = "udp", desc = "Wireguard IPv4", roles = ["master", "ha", "worker"] },
    { from = 51821, to = 51821, proto = "udp", desc = "Wireguard IPv6", roles = ["master", "ha", "worker"] },
    { from = 5001, to = 5001, proto = "tcp", desc = "Embedded registry", roles = ["master", "ha"] },
    { from = 22, to = 22, proto = "tcp", desc = "SSH access", roles = ["master", "ha", "worker"] },
    { from = 80, to = 80, proto = "tcp", desc = "HTTP access", roles = ["master", "ha", "worker"] },
    { from = 443, to = 443, proto = "tcp", desc = "HTTPS access", roles = ["master", "ha", "worker"] },
    { from = 53, to = 53, proto = "udp", desc = "DNS for CoreDNS", roles = ["master", "ha", "worker"] },
    { from = 5432, to = 5432, proto = "tcp", desc = "PostgreSQL access", roles = ["master"] }
  ]
}

# Security Group Resource
resource "openstack_networking_secgroup_v2" "k3s_sg" {
  name        = "${var.cluster_name}-${var.resource_name}-sg"
  description = "Security group for ${var.k3s_role} in cluster ${var.cluster_name}"
}

resource "openstack_networking_secgroup_rule_v2" "k3s_sg_rules" {
  for_each = { for idx, rule in local.ingress_rules : 
    "${rule.from}-${rule.to}-${rule.proto}-${rule.desc}" => rule
  }

  security_group_id = openstack_networking_secgroup_v2.k3s_sg.id
  direction         = "ingress"
  ethertype        = "IPv4"  # Fix: Add ethertype (mandatory)
  port_range_min   = each.value.from  # Fix: Correct OpenStack argument
  port_range_max   = each.value.to
  protocol         = each.value.proto
  remote_ip_prefix = "0.0.0.0/0"
  description      = each.value.desc
}

# outputs.tf
output "cluster_name" {
  value = var.k3s_role == "master" ? var.cluster_name : null
}

output "master_ip" {
  value = var.k3s_role == "master" ? openstack_compute_instance_v2.k3s_node.network.0.fixed_ip_v4 : null
}