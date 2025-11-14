from cluster_builder import Swarmchestrate

cluster_name = "compassionate-hawking"
resource_name = "aws-test-cp"

swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")
swarmchestrate.remove_node(cluster_name, resource_name)
