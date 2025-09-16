# variables.tf
variable "manifest_folder" {}
variable "ssh_private_key_path" {}
variable "master_ip" {}
variable "ssh_user" {}

#main.tf
resource "null_resource" "copy_manifests" {
  connection {
    type        = "ssh"
    user        = var.ssh_user
    private_key = file(var.ssh_private_key_path)
    host        = var.master_ip
    timeout     = "1m"
  }

  # Copy the folder specified by the variable
  provisioner "file" {
    source      = var.manifest_folder
    destination = "/home/ubuntu/manifests"
  }

  # Apply all manifests
  provisioner "remote-exec" {
    inline = [
      "sudo KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl apply -f /home/ubuntu/manifests/"
    ]
  }
}
