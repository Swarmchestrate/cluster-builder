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
variable "ssh_key" {
}
variable "master_ip" {
  default = null
}
variable "ha" {
  default = false
}

#main.tf
data "template_file" "user_data" {
  template = file("${path.module}/${var.k3s_role}_user_data.sh.tpl")
  vars = {
    k3s_token = var.k3s_token
    ha        = var.ha
    public_ip = var.edge_device_ip
    master_ip = var.master_ip
    resource_name = "${var.resource_name}"
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
    private_key = var.ssh_auth_method == "key" ? file(var.ssh_key) : null
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
    Name          = "${var.resource_name}"
    cluster_name  = var.cluster_name
    role          = var.k3s_role
    resource_name = var.resource_name
    edge_ip       = var.edge_device_ip
  }
  depends_on = [local_file.rendered_user_data]
}

# Local variables for outputs
locals {
   master_ip     = var.k3s_role == "master" ? var.edge_device_ip : var.master_ip
   worker_ip     = var.k3s_role == "worker" ? var.edge_device_ip : null
   ha_ip         = var.k3s_role == "ha" ? var.edge_device_ip : null
}

# Temporary state file in /tmp
resource "local_file" "edge_state" {
  content  = jsonencode({
    cluster_name  = var.cluster_name
    k3s_token     = var.k3s_token
    master_ip     = local.master_ip
    worker_ip     = local.worker_ip
    ha_ip         = local.ha_ip
    resource_name = var.resource_name
  })
  filename = "/tmp/${var.resource_name}_state.json"
}

# Delete the temporary state file after Terraform finishes
resource "null_resource" "cleanup_edge_state" {
  provisioner "local-exec" {
    command = "rm -f /tmp/${var.resource_name}_state.json"
  }

  depends_on = [local_file.edge_state]
}

# Outputs
output "cluster_name" {
  value = jsondecode(local_file.edge_state.content).cluster_name 
}
output "master_ip" {
  value = jsondecode(local_file.edge_state.content).master_ip 
}
output "worker_ip" {
  value = jsondecode(local_file.edge_state.content).worker_ip 
}
output "ha_ip" {
  value = jsondecode(local_file.edge_state.content).ha_ip 
}
output "k3s_token" {
  value = jsondecode(local_file.edge_state.content).k3s_token 
}
output "resource_name" {
  value = jsondecode(local_file.edge_state.content).resource_name 
}