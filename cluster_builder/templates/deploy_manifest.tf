# main.tf

variable "manifest_folder" {}
variable "ssh_private_key_path" {}
variable "master_ip" {}
variable "ssh_user" {}

resource "null_resource" "copy_manifests" {
  connection {
    type        = "ssh"
    user        = var.ssh_user
    private_key = file(var.ssh_private_key_path)
    host        = var.master_ip
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
