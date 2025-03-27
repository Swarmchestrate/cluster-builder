from config import pg_config
from cluster_builder import Swarmchestrate

CLUSTER_NAME = "boring_liskov"
NODE_NAME = "aws_sweet_swanson"

swarmchestrate = Swarmchestrate(
    template_dir="templates", output_dir="output", pg_config=pg_config
)
swarmchestrate.remove_node(CLUSTER_NAME, NODE_NAME)
