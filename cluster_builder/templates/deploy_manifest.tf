# main.tf

variable "manifest_folder" {}
variable "ssh_key" {
  default = ""
}
variable "ssh_password" {
  default   = ""
  sensitive = true
}
variable "ssh_auth_method" {
  default = "key"
}
variable "master_ip" {}
variable "ssh_user" {}
variable "ssh_port" {
  default     = 22
  description = "SSH port for the master node. Use non-22 for DDNS/NAT setups (e.g. 10000)."
}


resource "null_resource" "copy_manifests" {
  connection {
    type        = "ssh"
    user        = var.ssh_user
    private_key = var.ssh_auth_method == "key" ? file(var.ssh_key) : null
    password    = var.ssh_auth_method == "password" ? var.ssh_password : null
    host        = var.master_ip
    port        = var.ssh_port
  }

  # Copy manifest folder to a temporary location first
  provisioner "file" {
    source      = var.manifest_folder
    destination = "/tmp/manifests_temp/"
  }

  # Move manifests into K3s manifests folder atomically
  provisioner "remote-exec" {
    inline = [
      "sudo mv /tmp/manifests_temp/* /var/lib/rancher/k3s/server/manifests/"
    ]
  }
}
