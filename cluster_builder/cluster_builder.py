import re
import jinja2
import os
import subprocess
from names_generator import generate_name
from config import aws_config, pg_config

class Swarmchestrate:
    def __init__(self, template_dir, output_dir, variables=None):
        """
        Initialize the Swarmchestrate class.

        """
        self.template_dir = f"{template_dir}"
        self.output_dir = output_dir

    def get_cluster_output_dir(self, cluster_name):
        return os.path.join(self.output_dir, f"cluster_{cluster_name}")
    
    def generate_random_name(self):
        """Generate a readable random string using names-generator."""
        return generate_name()  # Example output: 'stoic_fermi'

    def generate_cluster_name(self):
        """Generate a human-readable cluster name."""
        return f"swarmchestrate_{self.generate_random_name()}"

    def substitute_values(self, config, subdir=None, random_name=None):
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
        
        # Add pg_config data to config to be rendered in templates
        conn_str = f"postgres://{pg_config['user']}:{pg_config['password']}@{pg_config['host']}:5432/{pg_config['database']}?sslmode={pg_config['sslmode']}"
        config["pg_conn_str"] = conn_str  # Add the connection string to the config

        config["random_name"] = random_name
         
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
        output_path = os.path.join(role_dir, f"{config['k3s_role']}_user_data.sh.tpl" ) # Removing '.j2'

        with open(output_path, 'w') as f:
            f.write(rendered_content)
        print(f"{cloud.upper()}: Rendered user_data.sh.tpl for {config['k3s_role'] } saved to: {output_path}")

    def get_target_resource(self, cloud):
        """
        Returns the appropriate OpenTofu resource type for the given cloud provider.
        """
        cloud_resource_map = {
            "aws": "aws_instance",
            "openstack": "openstack_compute_instance_v2"
        }
        return cloud_resource_map.get(cloud)

    def deploy_k3s_master(self, config):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        cloud = config["cloud"]

        # Generate a cluster name if not provided
        if "cluster_name" not in config:
            cluster_name = self.generate_cluster_name()
            config["cluster_name"] = cluster_name

        cluster_dir = self.get_cluster_output_dir(config["cluster_name"])
        random_name = self.generate_random_name()
        subdir = f"k3s_master_{cloud}_{random_name}"
        self.substitute_values(config, subdir, random_name)
        role_dir = os.path.join(cluster_dir, subdir)
        print(f"role dir: {role_dir}")
        
        # Get the correct resource type for OpenTofu
        resource_type = self.get_target_resource(cloud)

        # Generate the OpenTofu target string
        target = f"{resource_type}.k3s_master_{random_name}"
    
        self.deploy(config, target, role_dir)

    def deploy_k3s_ha(self, config):
        """
        Deploy the K3s HA cluster using OpenTofu.
        """
        cloud = config["cloud"]
        cluster_name = config["cluster_name"]
        cluster_dir = self.get_cluster_output_dir(cluster_name)
        random_name = self.generate_random_name()
        subdir = f"k3s_ha_{cloud}_{random_name}"
        self.substitute_values(config, subdir, random_name)
        
        role_dir = os.path.join(cluster_dir, subdir)
        print(f"role dir: {role_dir}")
        
        # Get the correct resource type for OpenTofu
        resource_type = self.get_target_resource(cloud)

        # Generate the OpenTofu target string
        target = f"{resource_type}.k3s_ha_{random_name}"
    
        self.deploy(config, target, role_dir)


    def deploy_k3s_worker(self, config):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        cloud = config["cloud"]
        cluster_name = config["cluster_name"]
        cluster_dir = self.get_cluster_output_dir(cluster_name)
        random_name = self.generate_random_name()
        subdir = f"k3s_worker_{cloud}_{random_name}"
        self.substitute_values(config, subdir, random_name)
        role_dir = os.path.join(cluster_dir, subdir)
        print(f"role dir: {role_dir}")
        # Get the correct resource type for OpenTofu
        resource_type = self.get_target_resource(cloud)

        # Generate the OpenTofu target string
        target = f"{resource_type}.k3s_worker_{random_name}"

        self.deploy(config, target, role_dir)

    def deploy(self, config, target, role_dir, dryrun=False):
        """
        Execute OpenTofu commands to deploy the K3s component with error handling.
        """
        try:
            print(f"Initializing OpenTofu for {config['cloud']} {config['k3s_role']} in {role_dir}...")
            subprocess.run(["tofu", "init"], check=True, cwd=role_dir)
            
            print(f"Planning infrastructure for {config['cloud']} {config['k3s_role']}...")
            subprocess.run(["tofu", "plan", f"-target={target}"], check=True, cwd=role_dir)
            
            print(f"Applying infrastructure for {config['cloud']} {config['k3s_role']}...")
            subprocess.run(["tofu", "apply", "-auto-approve", f"-target={target}"], check=True, cwd=role_dir)
            
        except subprocess.CalledProcessError as e:
            print(f"Error executing OpenTofu commands: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

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
   
swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")

swarmchestrate.deploy_k3s_master(aws_config)
#swarmchestrate.deploy_k3s_ha(aws_config)
#swarmchestrate.destroy("swarmchestrate_06z51q")
#swarmchestrate.deploy_k3s_ha(edge_config)
#swarmchestrate.deploy_k3s_master(aws_config)
#swarmchestrate.deploy_k3s_worker(aws_config)
