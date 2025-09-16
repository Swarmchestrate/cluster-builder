from cluster_builder import Swarmchestrate

CLUSTER_NAME = "mystifying-goldstine"
module_name = "aws-nifty-rubin"

swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")
swarmchestrate.remove_node(CLUSTER_NAME, module_name, is_edge=False)
