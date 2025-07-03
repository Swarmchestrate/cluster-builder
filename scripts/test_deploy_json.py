import json
from cluster_builder import Swarmchestrate

# Load JSON config from file
with open("node_config.json", "r") as f:
    json_config = json.load(f)

# Create Swarmchestrate instance
swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")

# Add node
swarmchestrate.add_node(json_config)
