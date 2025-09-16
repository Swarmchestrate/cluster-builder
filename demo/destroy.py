from cluster_builder import Swarmchestrate

CLUSTER_NAME = "great-benz"

swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")
swarmchestrate.destroy(CLUSTER_NAME)