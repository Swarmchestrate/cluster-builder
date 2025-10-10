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

  provisioner "remote-exec" {
    inline = [
      "sudo rm -rf /var/lib/rancher/k3s/server/manifests/*",
      "sudo cp -r ${var.manifest_folder}/* /var/lib/rancher/k3s/server/manifests/",
      "sudo chown -R root:root /var/lib/rancher/k3s/server/manifests/"
    ]
  }
}
