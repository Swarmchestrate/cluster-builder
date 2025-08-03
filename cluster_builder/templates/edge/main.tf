# variables.tf
variable "cluster_name" {}
variable "edge_device_ip" {}
variable "k3s_token" {}
variable "cloud" {
  default = "edge"
}
variable "k3s_role" {}
variable "resource_name" {}
variable "ssh_auth_method" {}
variable "ssh_user" {}
variable "ssh_password" {
  sensitive = true
  default = null
}
variable "ssh_private_key" {
  default = null
}
variable "master_ip" {
  default = null
}
variable "ha" {
  default = null
}

data "template_file" "user_data" {
  template = file("${path.module}/${var.k3s_role}_user_data.sh.tpl")
  vars = {
    k3s_token = var.k3s_token
    ha        = var.ha
    public_ip = var.edge_device_ip
    master_ip = var.master_ip
  }
}

resource "local_file" "rendered_user_data" {
  content  = data.template_file.user_data.rendered
  filename = "${path.module}/${var.k3s_role}_user_data.sh"
}

resource "null_resource" "deploy_k3s_edge" {
  connection {
    type        = "ssh"
    user        = var.ssh_user
    host        = var.edge_device_ip
    password    = var.ssh_auth_method == "password" ? var.ssh_password : null
    private_key = var.ssh_auth_method == "key" ? file(var.ssh_private_key) : null
  }

   provisioner "file" {
    source      = "${path.module}/${var.k3s_role}_user_data.sh"
    destination = "/tmp/edge_user_data.sh"
   }

   provisioner "remote-exec" {
    inline = [
      "rm -f ~/.ssh/known_hosts",
      "echo 'Executing remote provisioning script on ${var.k3s_role} node'",
      "chmod +x /tmp/edge_user_data.sh",
      "sudo /tmp/edge_user_data.sh"
    ]
  }

  triggers = {
    Name          = "K3s-${var.k3s_role}-${var.cluster_name}-${var.resource_name}"
    cluster_name  = var.cluster_name
    role          = var.k3s_role
    resource_name = var.resource_name
    edge_ip       = var.edge_device_ip
  }
}