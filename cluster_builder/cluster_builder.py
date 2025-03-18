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
    
    # def generate_cluster_name(self):
    #     """
    #     Generate a random cluster name.
    #     """
    #     random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    #     return f"swarmchestrate_{random_str}"
    # # if id is provided use that as cluster name, if not provided use above logic
    
    
    def generate_main_tf(self, config, subdir, random_name):
        """
        Dynamically generate main.tf based on the configuration.
        """
        cloud = config.get("cloud")
        cluster_name = config["cluster_name"]
        cluster_dir = self.get_cluster_output_dir(cluster_name)
        main_tf_path = os.path.join(cluster_dir, "main.tf")

        os.makedirs(cluster_dir, exist_ok=True)

        # Read existing content if main.tf exists
        if os.path.exists(main_tf_path):
            with open(main_tf_path, "r") as f:
                existing_content = f.read()
        else:
            existing_content = ""  # If it doesn't exist, start with an empty string

        print(f"PostgreSQL host: {pg_config['host']}") #debug
        # Generate the connection string
        conn_str = f"postgres://{pg_config['user']}:{pg_config['password']}@{pg_config['host']}:5432/{pg_config['database']}?sslmode={pg_config['sslmode']}"

# Terraform backend configuration
        backend_config = f"""
terraform {{
  backend "pg" {{
    conn_str = "{conn_str}"
    schema_name = "{cluster_name}"
  }}
}}
""".strip()

         # If backend config is already in existing content, remove duplicate
        if 'backend "pg"' not in existing_content:
            existing_content = backend_config + "\n\n" + existing_content.strip()


        new_content = existing_content

            # Define master module definition
        master_module_def = f"""
module "k3s_master" {{
  source = "./{subdir}"
}}
""".strip()

        # Check if module "k3s_master" exists, add or replace it
        if config["k3s_role"] == "master":
            if 'module "k3s_master"' not in existing_content:
                new_content += "\n\n" + master_module_def  # Add if it doesn't exist
            else:
                # Replace existing k3s_master module definition
                new_content = re.sub(r'module\s+"k3s_master"\s*{[^}]+}', master_module_def, new_content)

        if config["k3s_role"] in ["worker", "ha"]:
            module_name = f"{subdir}"
            module_def = f"""
module "{module_name}" {{
  source = "./{subdir}"
  master_ip         = "{config['master_ip']}"
  cluster_name      = "{config['cluster_name']}"
}}
""".strip()

            if f'module "{module_name}"' not in existing_content:
                new_content += "\n\n" + module_def
                 
        if new_content.strip() != existing_content.strip():
            print(f"Updated main.tf content:\n{new_content}")  # Debugging print
            with open(main_tf_path, "w") as f:
                f.write(new_content)

            print(f"Updated main.tf for {cloud} in {cluster_dir}.")


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
        output_path = os.path.join(cluster_dir, f"{config['k3s_role']}_user_data.sh.tpl" ) # Removing '.j2'

        with open(output_path, 'w') as f:
            f.write(rendered_content)
        print(f"{cloud.upper()}: Rendered user_data.sh.tpl for {config['k3s_role'] } saved to: {output_path}")

        self.generate_main_tf(config, subdir, random_name)

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
        random_name = self.generate_random_name()
        subdir = f"k3s_master_{cloud}_{random_name}"
        self.substitute_values(config, subdir, random_name)
        target = "module.k3s_master"
        self.deploy(config, target, cluster_dir)

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
        target = f"module.k3s_ha_{cloud}_{random_name}"
        self.deploy(config, target, cluster_dir)


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
        target = f"module.k3s_worker_{cloud}_{random_name}"
        self.deploy(config, target, cluster_dir)

    def deploy(self, config, target, cluster_dir, dryrun=False):
        """
        Execute OpenTofu commands to deploy the K3s component with error handling.
        """
        try:
            print(f"Initializing OpenTofu for {config['cloud']} {config['k3s_role']} in {cluster_dir}...")
            subprocess.run(["tofu", "init"], check=True, cwd=cluster_dir)
            
            print(f"Planning infrastructure for {config['cloud']} {config['k3s_role']}...")
            subprocess.run(["tofu", "plan", f"-target={target}"], check=True, cwd=cluster_dir)
            
            print(f"Applying infrastructure for {config['cloud']} {config['k3s_role']}...")
            subprocess.run(["tofu", "apply", "-auto-approve", f"-target={target}"], check=True, cwd=cluster_dir)
            
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
#swarmchestrate.deploy_k3s_worker(openstack_config)
