import json
from cluster_builder import Swarmchestrate
from demo.utils import write_outputs
import logging

logger = logging.getLogger("demo_RA")
# Load cluster configuration
with open("demo/lead_RA.json") as f:
    master_node = json.load(f)

# Initialize Swarmchestrate
swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")

print(f"[INFO] Deploying master node on cloud: {master_node['cloud']}")
outputs = swarmchestrate.add_node(master_node)

# Retrieve outputs
k3s_token = outputs.get("k3s_token")
cluster_name = outputs.get("cluster_name")
master_ip = outputs.get("master_ip")
node_name = outputs.get("node_name")

if not master_ip:
    logger.error("❌ Could not retrieve master IP from outputs for cluster '%s'", cluster_name or "unknown")
    raise RuntimeError("Could not retrieve master IP from outputs")

logger.info(f"[INFO] Cluster name: {cluster_name}")
logger.info(f"[INFO] Master IP: {master_ip}")
logger.info(f"[INFO] Master Node name: {node_name}")
# after deployment
write_outputs(cluster_name, master_ip, k3s_token, node_name)
logger.info(f"[INFO] Saved outputs for cluster: {cluster_name} in file")