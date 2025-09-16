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

  # Ensure the manifests folder exists on the remote host
  provisioner "remote-exec" {
    inline = [
      "mkdir -p /home/${var.ssh_user}/manifests",
      "sudo chmod 755 /home/${var.ssh_user}/manifests"
    ]
  }

  # Copy the manifests
  provisioner "file" {
    source      = var.manifest_folder
    destination = "/home/${var.ssh_user}"
  }

  # Apply manifests using K3s kubeconfig
  provisioner "remote-exec" {
    inline = [
    "sudo -E KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl apply -R -f /home/ubuntu/manifests/"
  ]
  }
}
