import json
from cluster_builder import Swarmchestrate
import logging

logger = logging.getLogger("test-deploy-cluster")
with open("scripts/cluster_config.json") as f:
    cluster_config = json.load(f)

k3s_token = cluster_config["k3s_token"]
nodes = cluster_config["nodes"]

swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")

# Deploy master first
master_node = next(node for node in nodes if node["k3s_role"] == "master")
master_node.update({
    "k3s_token": k3s_token,
})

logger.info(f"[INFO] Deploying master node on cloud: {master_node['cloud']}")

# add_node now returns a dict with cluster_name and master_ip
outputs = swarmchestrate.add_node(master_node)
master_ip = outputs.get("master_ip")
cluster_name = outputs.get("cluster_name")

if not master_ip:
    raise RuntimeError("Could not retrieve master IP from outputs")

logger.info(f"[INFO] Cluster name: {cluster_name}")
logger.info(f"[INFO] Master IP: {master_ip}")

# Deploy workers and HA nodes
for node in nodes:
    if node["k3s_role"] != "master":
        node.update({
            "k3s_token": k3s_token,
            "master_ip": master_ip,
            "cluster_name": cluster_name,
        })
        logger.info(f"[INFO] Deploying {node['k3s_role']} node on cloud: {node['cloud']}")
        swarmchestrate.add_node(node)
