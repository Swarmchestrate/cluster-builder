# variables.tf
# Determine whether to use block device
variable "use_block_device" {
  description = "Whether to use block storage volume as root device"
  type        = bool
  default     = false
}
variable "cluster_name" {}
variable "resource_name" {}
variable "k3s_role" {}
variable "master_ip" {
  default = null
}
variable "openstack_size" {}
variable "openstack_image_id" {}
variable "openstack_flavor_id" {}
variable "ssh_key_name" {}
variable "k3s_token" {}
variable "cloud" {
  default = "openstack"
}
variable "ha" {
  default = null
}

variable "network_id" {
  description = "The ID of the internal network to attach the instance to"
  type        = string
}
variable "ssh_user" {
  default = "ubuntu"
}
variable "ssh_private_key_path" {
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
  image_id    = var.openstack_image_id
}

# Compute instance for each role
resource "openstack_compute_instance_v2" "k3s_node" {
  name             = "${var.cluster_name}-${var.resource_name}"
  flavor_name       = var.openstack_flavor_id
  key_pair        = var.ssh_key_name
  security_groups = [openstack_networking_secgroup_v2.k3s_sg.id]


  dynamic "block_device" {
    for_each = var.use_block_device ? [1] : []
      content {
        uuid                  = openstack_blockstorage_volume_v3.root_volume[0].id
        source_type           = "volume"
        destination_type      = "volume"
        boot_index            = 0
        delete_on_termination = true
    }
  }

  network {
    uuid = var.network.id
  }

   tags = [
    "${var.cluster_name}-${var.resource_name}",
    "ClusterName=${var.cluster_name}",
    "Role=${var.k3s_role}"
  ]
}

# Floating IP allocation
resource "openstack_networking_floatingip_v2" "fip" {
  pool = var.external_network_name
}

# Associate Floating IP with the instance
resource "openstack_compute_floatingip_associate_v2" "fip_assoc" {
  floating_ip = openstack_networking_floatingip_v2.fip.address
  instance_id = openstack_compute_instance_v2.k3s_node.id
}

# Provisioning via SSH
resource "null_resource" "k3s_provision" {
  depends_on = [openstack_compute_floatingip_associate_v2.fip_assoc]

  provisioner "file" {
    content = templatefile("${path.module}/${var.k3s_role}_user_data.sh.tpl", {
      ha           = var.ha,
      k3s_token    = var.k3s_token,
      master_ip    = var.master_ip,
      cluster_name = var.cluster_name,
      public_ip = openstack_networking_floatingip_v2.fip.address
    })
    destination = "/tmp/k3s_user_data.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/k3s_user_data.sh",
      "sudo /tmp/k3s_user_data.sh"
    ]
  }

  connection {
    type        = "ssh"
    user        = var.ssh_user
    private_key = file(var.ssh_private_key_path)
    host        = openstack_networking_floatingip_v2.fip.address
  }

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