from cluster_builder.utils.hcl import remove_module_block

main_tf_path = "/workspaces/cluster-builder/output/cluster_quirky-jang/main.tf"

module_name = "aws-romantic-bardeen"

remove_module_block(main_tf_path, module_name)
