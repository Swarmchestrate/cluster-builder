
from config import aws_config, pg_config
from cluster_builder.cluster_builder import Swarmchestrate

swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output", pg_config=pg_config)
swarmchestrate.deploy_k3s_master(aws_config)