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

  # Copy the manifest folder into /tmp
  provisioner "file" {
    source      = var.manifest_folder
    destination = "/tmp/"
  }

  # Apply namespace.yaml first if exists
  provisioner "remote-exec" {
    inline = [
      "folder_name=$(basename ${var.manifest_folder})",
      "if [ -f /tmp/$folder_name/namespace.yaml ]; then sudo -E KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl apply -f /tmp/$folder_name/namespace.yaml; fi"
    ]
  }

  # Apply the rest of the manifests
  provisioner "remote-exec" {
    inline = [
      "folder_name=$(basename ${var.manifest_folder})",
      "sudo -E KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl apply -R -f /tmp/$folder_name"
    ]
  }
}
