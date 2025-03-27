from config import aws_config, pg_config
from cluster_builder import Swarmchestrate

# aws_config["cluster_name"] = "crazy_wescoff"
# aws_config["k3s_role"] = "worker"
# aws_config["master_ip"] = "x.x.x.x"

swarmchestrate = Swarmchestrate(
    template_dir="templates", output_dir="output", pg_config=pg_config
)
swarmchestrate.create_cluster(aws_config)
