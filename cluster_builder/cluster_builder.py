import jinja2
import os
import subprocess
import random
import string
from config import aws_config, openstack_config, edge_config
from pg_backend import PGBackend

class Swarmchestrate:
    def __init__(self, template_dir, output_dir, variables=None):
        """
        Initialize the Swarmchestrate class.

        """
        self.template_dir = f"{template_dir}"
        self.output_dir = output_dir
        self.pg_backend = PGBackend()

    def get_cluster_output_dir(self, cluster_name):
        return os.path.join(self.output_dir, f"cluster-{cluster_name}")
    
    def generate_cluster_name(self):
        """
        Generate a random cluster name.
        """
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"swarmchestrate-{random_str}"
    
    def generate_main_tf(self, config):
        """
        Dynamically generate main.tf based on the configuration.
        """
        cloud = config.get("cloud")
        cluster_name = config["cluster_name"]
        cluster_dir = self.get_cluster_output_dir(cluster_name)

        os.makedirs(cluster_dir, exist_ok=True)

        main_tf_content = f"""
module "k3s_master" {{
  source = "./k3s_master_{cloud}"
}}
"""

        if config.get(f"{cloud}_ha_server_count", 0) > 0:
            main_tf_content += f"""
module "k3s_ha_{cloud}" {{
  source = "./k3s_ha_{cloud}"
  master_ip         = module.k3s_master.master_ip
  cluster_name      = module.k3s_master.cluster_name
  security_group_id = module.k3s_master.security_group_id
}}
"""

        for i in range(config.get(f"{cloud}_worker_count", 0)):
            main_tf_content += f"""
module "k3s_worker_{cloud}_{i}" {{
  source = "./k3s_worker_{cloud}_{i}"
  master_ip         = module.k3s_master.master_ip
  cluster_name      = module.k3s_master.cluster_name
  security_group_id = module.k3s_master.security_group_id
}}
"""
        with open(os.path.join(cluster_dir, "main.tf"), "w") as f:
            f.write(main_tf_content.strip())

        print(f"Generated main.tf for {cloud} in {cluster_dir}.")
        # Insert cluster state into the PG database
        self.pg_backend.insert_state(cluster_name, "main.tf", "generated", "success", {"content": main_tf_content})


    def substitute_values(self, config, subdir=None):
        """
        Substitute values into Jinja2 templates and save the rendered files.
        This method will render main.tf, network_security_group, and other templates into their respective folders.
        """
        cloud = config["cloud"]
        cluster_name = config["cluster_name"]  # Always use the existing cluster name
        cluster_dir = self.get_cluster_output_dir(cluster_name)
        os.makedirs(cluster_dir, exist_ok=True)  # Create the cluster folder if not already present

        cloud_template_dir = os.path.join(self.template_dir, cloud)
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.template_dir))

        role_dir = os.path.join(cluster_dir, subdir)
        os.makedirs(role_dir, exist_ok=True)

        for template_name in os.listdir(cloud_template_dir):
            if template_name.endswith('.j2'):
                template = env.get_template(f"{cloud}/{template_name}")
                rendered_content = template.render(config)
                output_path = os.path.join(role_dir, template_name[:-3])  # Removing '.j2'

                with open(output_path, 'w') as f:
                    f.write(rendered_content)
                print(f"{cloud.upper()}: Rendered {template_name} for {config['k3s_role'] } saved to: {output_path}")
        
        template = env.get_template("user_data.sh.tpl.j2")
        rendered_content = template.render(config)
        output_path = os.path.join(cluster_dir, f"{config['k3s_role']}_user_data.sh.tpl" ) # Removing '.j2'

        with open(output_path, 'w') as f:
            f.write(rendered_content)
        print(f"{cloud.upper()}: Rendered user_data.sh.tpl for {config['k3s_role'] } saved to: {output_path}")

        self.generate_main_tf(config)

    def deploy_k3s_master(self, config):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        cloud = config["cloud"]

        # Generate a cluster name if not provided
        if "cluster_name" not in config:
            cluster_name = self.generate_cluster_name()
        
        config["cluster_name"] = cluster_name

        cluster_dir = self.get_cluster_output_dir(cluster_name)
        config["k3s_role"] = "master"
        
        # Create table for the cluster in PostgreSQL
        self.pg_backend.create_table_for_cluster(cluster_name)
        
        self.substitute_values(config, f"k3s_master_{cloud}")
        target = "module.k3s_master"
        self.deploy(config, target, cluster_dir)


    def deploy_k3s_ha(self, config):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        cloud = config["cloud"]
        cluster_name = config["cluster_name"]
        cluster_dir = self.get_cluster_output_dir(cluster_name)
        config["k3s_role"] = "ha"
        self.substitute_values(config, f"k3s_ha_{cloud}")
        target = "module.k3s_ha"
        self.deploy(config, target, cluster_dir)


    def deploy_k3s_worker(self, config):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        cloud = config["cloud"]
        cluster_name = config["cluster_name"]
        cluster_dir = self.get_cluster_output_dir(cluster_name)
        config["k3s_role"] = "worker"

        worker_count = config.get(f"{cloud}_worker_count", 0)

        for i in range(worker_count):
            subdir = f"k3s_worker_{cloud}_{i}"
            self.substitute_values(config, subdir)
            target = f"module.k3s_worker_{cloud}_{i}"
            self.deploy(config, target, cluster_dir)


    def deploy(self, config, target, cluster_dir, dryrun=False):
        """
        Execute the OpenTofu commands to deploy the K3s component.
        """
        print(f"Initializing OpenTofu for {config['cloud']} {config['k3s_role']} in {cluster_dir}...")
        subprocess.run(["tofu", "init"], check=True, cwd=cluster_dir)
        print(f"Planning infrastructure for {config['cloud']} {config['k3s_role']}...")
        subprocess.run(["tofu", "plan", f"-target={target}"], check=True, cwd=cluster_dir)
        print(f"Applying infrastructure for {config['cloud']} {config['k3s_role']}...")
        subprocess.run(["tofu", "apply", "-auto-approve", f"-target={target}"], check=True, cwd=cluster_dir)

    def destroy(self, cluster_name):
        """
        Destroy the deployed K3s cluster for the specified cluster_name using OpenTofu.
        """
        print(f"Destroying the K3s cluster '{cluster_name}'...")

        # Get the directory for the specified cluster
        cluster_dir = self.get_cluster_output_dir(cluster_name)

        if not os.path.exists(cluster_dir):
            print(f"Error: Cluster directory '{cluster_dir}' not found.")
            return

        try:
            print(f"Planning destruction for cluster '{cluster_name}'...")
            subprocess.run(["tofu", "plan", "-destroy"], check=True, cwd=cluster_dir)

            print(f"Destroying infrastructure for cluster '{cluster_name}'...")
            subprocess.run(["tofu", "destroy", "-auto-approve"], check=True, cwd=cluster_dir)

            print(f"Cluster '{cluster_name}' destroyed successfully.")
    
        except subprocess.CalledProcessError as e:
            print(f"Error during destruction of cluster '{cluster_name}': {e}")

        except Exception as e:
            print(f"An unexpected error occurred during destruction of cluster '{cluster_name}': {e}")
        finally:
            # Clean up the state from PG if necessary
            self.pg_backend.insert_state(cluster_name, "destruction", "complete", "success", {})
   
swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")


#swarmchestrate.deploy_k3s_master(aws_config)
swarmchestrate.deploy_k3s_ha(edge_config)
#swarmchestrate.deploy_k3s_master(aws_config)
#swarmchestrate.deploy_k3s_worker(openstack_config)

# delay_seconds = 5 * 60
# print(f"Waiting for {delay_seconds / 60} minutes before destroying resources...")
# time.sleep(delay_seconds)

# print("Starting the destruction process...")
# swarmchestrate.destroy()