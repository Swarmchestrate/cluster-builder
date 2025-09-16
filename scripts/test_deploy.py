# Import your AWS or OpenStack configuration
from .config import aws_config
from cluster_builder import Swarmchestrate

# aws_config["cluster_name"] = "crazy_wescoff"
# aws_config["k3s_role"] = "worker"
# aws_config["master_ip"] = "x.x.x.x"

swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")
# Add the node with given config
swarmchestrate.add_node(aws_config)
