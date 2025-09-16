from cluster_builder import Swarmchestrate

CLUSTER_NAME = "vigorous-panini"

swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")
swarmchestrate.destroy(CLUSTER_NAME)