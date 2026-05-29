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
variable "ssh_port" {
  default = 22
}
variable "namespace" {
  default = "default"
}

resource "null_resource" "docker_registry_secrets" {
  count = length(var.registries)

  connection {
    type        = "ssh"
    host        = var.master_ip
    user        = var.ssh_user
    private_key = var.ssh_auth_method == "key" ? file(var.ssh_key) : null
    password    = var.ssh_auth_method == "password" ? var.ssh_password : null
    port        = var.ssh_port
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