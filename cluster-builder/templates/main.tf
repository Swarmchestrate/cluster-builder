module "k3s_master" {
  source = "./k3s_master"
}

module "k3s_ha" {
  source = "./k3s_ha"
  master_ip     = module.k3s_master.master_ip
  cluster_name = module.k3s_master.cluster_name
  security_group_id = module.k3s_master.security_group_id
}

module "k3s_worker_one" {
  source = "./k3s_worker_one"
  master_ip     = module.k3s_master.master_ip
  cluster_name = module.k3s_master.cluster_name
  security_group_id = module.k3s_master.security_group_id
}
