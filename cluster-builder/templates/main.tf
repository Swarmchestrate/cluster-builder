module "k3s_master" {
  source = "./k3s_master"
}

module "k3s_ha" {
  source = "./k3s_ha"
}

module "k3s_worker_one" {
  source = "./k3s_worker_one"
}
