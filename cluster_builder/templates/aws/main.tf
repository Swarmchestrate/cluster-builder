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
variable "ssh_private_key_path" {}
variable "ssh_key_name" {}
variable "k3s_token" {}
variable "cloud" {}
variable "ha" {
  default = false
}
variable "security_group_id" {
  default = ""
}
variable "tcp_ports" {
  default = []
}
variable "udp_ports" {
  default = []
}

#main.tf
locals {
  ingress_rules = var.security_group_id == "" ? concat(
    [
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
    ],
    [
      for port in var.tcp_ports : {
        from = port, to = port, proto = "tcp", desc = "Custom TCP rule for port ${port}", roles = ["master", "ha", "worker"]
      }
    ],
    [
      for port in var.udp_ports : {
        from = port, to = port, proto = "udp", desc = "Custom UDP rule for port ${port}", roles = ["master", "ha", "worker"]
      }
    ]
  ) : []
}
resource "aws_security_group" "k3s_sg" {
  count       = var.security_group_id == "" ? 1 : 0
  name        = "${var.k3s_role}-${var.cluster_name}-${var.resource_name}"
  description = "Security group for K3s node in cluster ${var.cluster_name}"

  dynamic "ingress" {
  for_each = { for idx, rule in local.ingress_rules : idx => rule if contains(rule.roles, var.k3s_role) }
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

resource "aws_instance" "k3s_node" {
  ami                    = var.ami
  instance_type          = var.instance_type
  key_name               = var.ssh_key_name

  # Use the provided security group ID if available or the one created by the security group resource.
  vpc_security_group_ids = var.security_group_id != "" ? [var.security_group_id] : [aws_security_group.k3s_sg[0].id]

  tags = {
    Name        = "${var.resource_name}"
    ClusterName = var.cluster_name
    Role        = var.k3s_role
  }

  # Upload the rendered user data script to the VM
  provisioner "file" {
    content = templatefile("${path.module}/${var.k3s_role}_user_data.sh.tpl", {
      ha           = var.ha,
      k3s_token    = var.k3s_token,
      master_ip    = var.master_ip,
      cluster_name = var.cluster_name,
      public_ip  = self.public_ip,
      resource_name = "${var.resource_name}"
    })
    destination = "/tmp/k3s_user_data.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "rm -f ~/.ssh/known_hosts",
      "echo 'Executing remote provisioning script on ${var.k3s_role} node'",
      "chmod +x /tmp/k3s_user_data.sh",
      "sudo /tmp/k3s_user_data.sh"
    ]
  }

  connection {
    type        = "ssh"
    user        = var.ssh_user
    private_key = file(var.ssh_private_key_path)
    host        = self.public_ip
  }
}

# outputs.tf
output "cluster_name" {
  value = var.cluster_name
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
  value = var.k3s_token
}

output "instance_status" {
  value = aws_instance.k3s_node.id
}

output "resource_name" {
  value = aws_instance.k3s_node.tags["Name"]
}