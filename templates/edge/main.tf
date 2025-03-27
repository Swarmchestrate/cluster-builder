# variables.tf
variable "cluster_name" {}
variable "edge_device_ip" {}
variable "ssh_user" {}
variable "ssh_password" {}
variable "k3s_token" {}
variable "k3s_role" {}
variable "resource_name" {}
variable "master_ip" {}

resource "null_resource" "k3s_edge" {

  connection {
    type        = "ssh"
    user        = var.ssh_user
    password    = var.ssh_password
    host        = var.edge_device_ip
  }

  provisioner "file" {
    source      = "${var.k3s_role}_user_data.sh"
    destination = "/tmp/edge_user_data.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/edge_user_data.sh",
      "sudo K3S_TOKEN='${var.k3s_token}' " 
    "${var.k3s_role != "master" ? "MASTER_IP=${var.master_ip} " : ""}"
    "/tmp/edge_user_data.sh"
    ]
  }

triggers = {
    Name         = "${var.k3s_role}-${var.cluster_name}-${var.resource_name}"
    cluster_name = var.cluster_name
    role         = var.k3s_role
    random_name  = var.random_name
  }
}
