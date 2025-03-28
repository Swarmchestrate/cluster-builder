# variables.tf
variable "cluster_name" {}
variable "resource_name" {}
variable "k3s_role" {}
variable "master_ip" {
  default = null
}
variable "ami" {}
variable "instance_type" {}
variable "ssh_key_name" {}
variable "k3s_token" {}
variable "cloud" {
  default = null
}
variable "ha" {
  default = null
}

# main.tf
resource "aws_instance" "k3s_node" {
  ami                    = var.ami
  instance_type          = var.instance_type
  key_name               = var.ssh_key_name

  vpc_security_group_ids = [
    aws_security_group.k3s_sg.id
  ]

  user_data = templatefile(
    "${path.module}/${var.k3s_role}_user_data.sh.tpl",
    {
      ha            = var.ha,
      k3s_token     = var.k3s_token,
      master_ip     = var.master_ip,
      cluster_name  = var.cluster_name
    }
  )

  tags = {
    Name        = "${var.cluster_name}-${var.resource_name}"
    ClusterName = var.cluster_name
    Role        = var.k3s_role
  }
}

resource "aws_security_group" "k3s_sg" {
  name        = "${var.k3s_role}-${var.cluster_name}-${var.resource_name}"
  description = "Security group for K3s node in cluster ${var.cluster_name}"

  dynamic "ingress" {
    for_each = toset([
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
    ])
    content {
      from_port   = ingress.value.from
      to_port     = ingress.value.to
      protocol    = ingress.value.proto
      cidr_blocks = ["0.0.0.0/0"]
      description = ingress.value.desc
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.k3s_role}-${var.cluster_name}-${var.resource_name}"
  }
}

# outputs.tf
output "cluster_name" {
  value = var.k3s_role == "master" ? var.cluster_name : null
}

output "master_ip" {
  value = var.k3s_role == "master" ? aws_instance.k3s_node.public_ip : null
}
