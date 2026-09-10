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

resource "null_resource" "remove_manifests" {
  connection {
    type        = "ssh"
    user        = var.ssh_user
    private_key = var.ssh_auth_method == "key" ? file(var.ssh_key) : null
    password    = var.ssh_auth_method == "password" ? var.ssh_password : null
    host        = var.master_ip
    port        = var.ssh_port
  }

  # Remove each manifest that was previously deployed so k3s prunes its resources
  provisioner "remote-exec" {
    inline = concat(
      [for f in fileset(var.manifest_folder, "*") : "sudo rm -f /var/lib/rancher/k3s/server/manifests/${f}"],
      [
        # Also clean up deployments/services created by apps the manifest launched afterwards,
        # keeping the built-in "kubernetes" service intact
        "sudo kubectl delete deployments --all -n default --ignore-not-found",
        "sudo kubectl get services -n default --no-headers -o custom-columns=:metadata.name | grep -v '^kubernetes$' | xargs -r sudo kubectl delete service -n default --ignore-not-found"
      ]
    )
  }
}
