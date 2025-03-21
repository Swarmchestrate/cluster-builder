from cluster_builder.utils.hcl import remove_module_block

main_tf_path = "./test-out/main.tf"

module_name = "worker_xyz123"

remove_module_block(main_tf_path, module_name)
