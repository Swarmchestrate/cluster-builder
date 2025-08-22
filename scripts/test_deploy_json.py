import json
from cluster_builder import Swarmchestrate
import logging

logger = logging.getLogger("test-deploy")

with open("scripts/node_config.json", "r") as f:
    config = json.load(f)

nodes = config.get("nodes", [])
swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")

for node in nodes:
    logger.info(f"[INFO] Provisioning {node['k3s_role']} node on {node['cloud']}")
    swarmchestrate.add_node(node)
