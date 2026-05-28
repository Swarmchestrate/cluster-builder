terraform {
  required_providers {
    k3s = {
      source = "striveworks/k3s"
      version = "1.0.0"
    }
  }
}
# variables.tf
variable "cluster_name" {}
variable "resource_name" {}
variable "k3s_role" {}
variable "master_ip" {
  default = null
}
variable "ami" {}
variable "instance_type" {}
variable "ssh_user" {}
variable "ssh_key" {}
variable "k3s_token" {}
variable "cloud" {}
variable "ha" {
  default = false
}
variable "security_group_id" {
  default = ""
}
variable "custom_ingress_ports" {
  type = list(object({
    from     = number
    to       = number
    protocol = string
    source   = string
  }))
  default = []
}
variable "custom_egress_ports" {
  type = list(object({
    from        = number
    to          = number
    protocol    = string
    destination = string
  }))
  default = []
}

# main.tf
locals {
  default_rules = [
    { from = 2379, to = 2380,  protocol = "tcp", desc = "etcd communication",    roles = ["master", "ha"] },
    { from = 6443, to = 6443,  protocol = "tcp", desc = "K3s API server",        roles = ["master", "ha", "worker"] },
    { from = 8472, to = 8472,  protocol = "udp", desc = "VXLAN for Flannel",     roles = ["master", "ha", "worker"] },
    { from = 10250, to = 10250, protocol = "tcp", desc = "Kubelet metrics",      roles = ["master", "ha", "worker"] },
    { from = 51820, to = 51820, protocol = "udp", desc = "Wireguard IPv4",       roles = ["master", "ha", "worker"] },
    { from = 51821, to = 51821, protocol = "udp", desc = "Wireguard IPv6",       roles = ["master", "ha", "worker"] },
    { from = 5001,  to = 5001,  protocol = "tcp", desc = "Embedded registry",    roles = ["master", "ha"] },
    { from = 22,    to = 22,    protocol = "tcp", desc = "SSH access",           roles = ["master", "ha", "worker"] },
    { from = 80,    to = 80,    protocol = "tcp", desc = "HTTP access",          roles = ["master", "ha", "worker"] },
    { from = 443,   to = 443,   protocol = "tcp", desc = "HTTPS access",         roles = ["master", "ha", "worker"] },
    { from = 53,    to = 53,    protocol = "udp", desc = "DNS for CoreDNS",      roles = ["master", "ha", "worker"] },
    { from = 5432,  to = 5432,  protocol = "tcp", desc = "PostgreSQL access",    roles = ["master"] }
  ]
}

resource "aws_security_group" "k3s_sg" {
  count       = var.security_group_id == "" ? 1 : 0
  name        = "${var.k3s_role}-${var.cluster_name}-${var.resource_name}"
  description = "Security group for K3s node in cluster ${var.cluster_name}"

  dynamic "ingress" {
    for_each = {
      for idx, rule in concat(
        local.default_rules,
        [
          for i in range(length(var.custom_ingress_ports)) : {
            from     = var.custom_ingress_ports[i].from
            to       = var.custom_ingress_ports[i].to
            protocol = var.custom_ingress_ports[i].protocol
            desc     = "Custom rule for ${var.custom_ingress_ports[i].protocol}"
            roles    = ["master", "ha", "worker"]
            source   = var.custom_ingress_ports[i].source
          }
        ]
      ) : idx => rule if contains(rule.roles, var.k3s_role)
    }
    content {
      from_port   = ingress.value.from
      to_port     = ingress.value.to
      protocol    = ingress.value.protocol
      cidr_blocks = [lookup(ingress.value, "source", "0.0.0.0/0")]
      description = ingress.value.desc
    }
  }

  dynamic "egress" {
    for_each = {
      for idx, rule in concat(
        [
          {
            from        = 0
            to          = 0
            protocol    = "-1"
            destination = "0.0.0.0/0"
            desc        = "Default allow all egress"
          }
        ],
        var.custom_egress_ports
      ) : idx => rule
    }
    content {
      from_port   = egress.value.from
      to_port     = egress.value.to
      protocol    = egress.value.protocol
      cidr_blocks = [lookup(egress.value, "destination", "0.0.0.0/0")]
      description = lookup(egress.value, "desc", "Custom egress rule")
    }
  }

  tags = {
    Name = "${var.k3s_role}-${var.cluster_name}-${var.resource_name}"
  }
}

resource "aws_instance" "k3s_node" {
  ami           = var.ami
  instance_type = var.instance_type
  key_name      = replace(basename(var.ssh_key), ".pem", "")

  vpc_security_group_ids = var.security_group_id != "" ? [var.security_group_id] : [aws_security_group.k3s_sg[0].id]

  tags = {
    Name        = var.resource_name
    k3sToken    = var.k3s_token
    ClusterName = var.cluster_name
    Role        = var.k3s_role
  }
}

# Standalone master (no HA)
resource "k3s_server" "k3s" {
  count = (var.k3s_role == "master" && !var.ha) ? 1 : 0

  auth = {
    host        = aws_instance.k3s_node.public_ip,
    user        = var.ssh_user,
    private_key_file = var.ssh_key
  }

  bootstrap_token = var.k3s_token

  config = <<-EOT
    node-name: ${var.resource_name}
    node-label: labels.swarmchestrate.eu/ms_id=${var.resource_name}
    cluster-name: ${var.cluster_name}
  EOT

  depends_on = [aws_instance.k3s_node]
}

# HA init node — first server that bootstraps the cluster
resource "k3s_server" "k3s_ha_init" {
  count = (var.k3s_role == "master" && var.ha) ? 1 : 0

  auth = {
    host        = aws_instance.k3s_node.public_ip,
    user        = var.ssh_user,
    private_key_file = var.ssh_key
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

  depends_on = [aws_instance.k3s_node]
}

# HA join node — subsequent server nodes joining an existing master
resource "k3s_server" "k3s_ha_join" {
  count = var.k3s_role == "ha" ? 1 : 0

  auth = {
    host        = aws_instance.k3s_node.public_ip,
    user        = var.ssh_user,
    private_key_file = var.ssh_key
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

  depends_on = [aws_instance.k3s_node]
}

# Worker node
resource "k3s_agent" "k3s" {
  count = var.k3s_role == "worker" ? 1 : 0

  auth = {
    host        = aws_instance.k3s_node.public_ip,
    user        = var.ssh_user,
    private_key_file = var.ssh_key
  }

  server = "https://${var.master_ip}:6443"
  token  = var.k3s_token

  config = <<-EOT
    node-name: ${var.resource_name}
    node-label: labels.swarmchestrate.eu/ms_id=${var.resource_name}
  EOT

  depends_on = [aws_instance.k3s_node]
}

# outputs.tf
output "cluster_name" {
  value = aws_instance.k3s_node.tags["ClusterName"]
}

output "k3s_role" {
  value = aws_instance.k3s_node.tags["Role"]
}

output "master_ip" {
  value = var.k3s_role == "master" ? aws_instance.k3s_node.public_ip : var.master_ip
}

output "worker_ip" {
  value = var.k3s_role == "worker" ? aws_instance.k3s_node.public_ip : null
}

output "ha_ip" {
  value = var.k3s_role == "ha" ? aws_instance.k3s_node.public_ip : null
}

output "k3s_token" {
  value = aws_instance.k3s_node.tags["k3sToken"]
}

output "instance_status" {
  value = aws_instance.k3s_node.id
}

output "resource_name" {
  value = aws_instance.k3s_node.tags["Name"]
}
