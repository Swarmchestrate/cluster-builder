from cluster_builder.utils.hcl import add_module_block

main_tf_path = "./test-out/main.tf"

module_name = "worker_xyz132"

# Config dictionary containing both cluster and module specific data
config = {
    "module_source": "/opt/modules/aws_node",
    "cluster_name": "cluster-a",
    "k3s_role": "worker",
    "random_name": "xyz123",
    "aws_region": "eu-west-2",
    "aws_access_key": "AKIA...",
    "aws_secret_key": "SECRET",
    "ami": "ami-abc",
    "instance_type": "t3a.small",
    "ssh_key_name": "my-key",
    "k3s_token": "abc123",
    "pg_conn_str": "postgres://...",
}

# Add module block to main.tf
add_module_block(main_tf_path, module_name, config)