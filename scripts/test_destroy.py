
from config import pg_config
from cluster_builder.cluster_builder import Swarmchestrate

CLUSTER_NAME = "vigorous_pare"

swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output", pg_config=pg_config)
swarmchestrate.destroy(CLUSTER_NAME)