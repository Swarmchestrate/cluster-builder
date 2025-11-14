variable "registries" {
  type = list(string)
}

variable "usernames" {
  type = list(string)
}

variable "passwords" {
  type = list(string)
}

variable "secret_names" {
  type    = list(string)
  default = []
}

variable "master_ip" {}
variable "ssh_user" {}
variable "ssh_private_key_path" {}
variable "namespace" {
  default = "default"
}

resource "null_resource" "docker_registry_secrets" {
  count = length(var.registries)

  connection {
    type        = "ssh"
    host        = var.master_ip
    user        = var.ssh_user
    private_key = file(var.ssh_private_key_path)
  }

  provisioner "remote-exec" {
    inline = [
      <<EOT
        SECRET_NAME=${length(var.secret_names) > 0 ? var.secret_names[count.index] : "regcred-${count.index}"}
        sudo -E KUBECONFIG=/etc/rancher/k3s/k3s.yaml kubectl create secret docker-registry $SECRET_NAME \
          --docker-server="${var.registries[count.index]}" \
          --docker-username="${var.usernames[count.index]}" \
          --docker-password="${var.passwords[count.index]}" \
          --namespace="${var.namespace}" \
          --dry-run=client -o yaml | sudo kubectl apply -f -
      EOT
    ]
  }
}

output "docker_registry_secret_names" {
  value = [for i in range(length(var.registries)) : length(var.secret_names) > 0 ? var.secret_names[i] : "regcred-${i}"]
}