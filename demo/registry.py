from cluster_builder import Swarmchestrate
import logging

logger = logging.getLogger("registry")

# Create a Swarmchestrate instance
swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")

# Cluster configuration for testing
registry_config = {
    "master_ip": "34.201.107.206",
    "ssh_user": "ec2-user",
    "ssh_private_key_path": "/workspaces/cluster-builder/output/g.pem",
    "secret_names": ["test"]
}

# Run the registry secret creation
swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")
swarmchestrate.create_registry_secrets(registry_config)

logger.info("✅ Registry secrets creation test completed")