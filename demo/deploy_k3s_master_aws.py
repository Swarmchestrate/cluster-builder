import json
from cluster_builder import Swarmchestrate
from demo.utils import write_outputs
import logging

logger = logging.getLogger("k3s_master")
# Load cluster configuration
with open("demo/k3s_server_aws.json") as f:
    master_node = json.load(f)

# Initialize Swarmchestrate
swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")

print(f"[INFO] Deploying master node on cloud: {master_node['cloud']}")
outputs = swarmchestrate.add_node(master_node)

# Retrieve outputs
k3s_token = outputs.get("k3s_token")
cluster_name = outputs.get("cluster_name")
master_ip = outputs.get("master_ip")
resource_name = outputs.get("resource_name")

if not master_ip:
    logger.error("❌ Could not retrieve master IP from outputs for cluster '%s'", cluster_name or "unknown")
    raise RuntimeError("Could not retrieve master IP from outputs")

logger.info(f"[INFO] Cluster name: {cluster_name}")
logger.info(f"[INFO] Master IP: {master_ip}")
logger.info(f"[INFO] Master Node name: {resource_name}")
# after deployment
write_outputs(cluster_name, master_ip, k3s_token)
logger.info(f"[INFO] Saved outputs for cluster: {cluster_name} in file")