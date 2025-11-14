import json
from cluster_builder import Swarmchestrate
from demo.utils import read_outputs
import logging

logger = logging.getLogger("k3s_worker")

def read_input_config():
    with open("demo/k3s_worker_openstack.json") as f:
        return json.load(f)

# Script execution
cluster_config = read_input_config()
base_data = read_outputs()  # reads lead_RA_outputs.json

cluster_name = base_data["cluster_name"]
master_ip = base_data["master_ip"]
k3s_token = base_data["k3s_token"]

swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")

for node in cluster_config["nodes"]:
    node.update({
        "k3s_token": k3s_token,
        "master_ip": master_ip,
        "cluster_name": cluster_name,
    })
    logger.info(f"[INFO] Deploying {node['k3s_role']} node on cloud: {node['cloud']}")
    outputs = swarmchestrate.add_node(node)
    
    # Retrieve outputs
    resource_name = outputs.get("resource_name")
    worker_ip = outputs.get("worker_ip")
logger.info(f"[INFO] Cluster {cluster_name} updated with nodes from this RA.") 
logger.info(f"[INFO] Worker IP: {worker_ip}")
logger.info(f"[INFO] Worker Node name: {resource_name}")
