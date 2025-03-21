import os
import subprocess
import shutil

from names_generator import generate_name

from cluster_builder.utils import hcl

class Swarmchestrate:
    def __init__(self, template_dir, output_dir, pg_config, variables=None):
        """
        Initialize the Swarmchestrate class.

        """
        self.template_dir = f"{template_dir}"
        self.output_dir = output_dir
        self.pg_config = pg_config

    def get_cluster_output_dir(self, cluster_name):
        return os.path.join(self.output_dir, f"cluster_{cluster_name}")
    
    def generate_random_name(self):
        """Generate a readable random string using names-generator."""
        return generate_name()

    def prepare_modules(self, config):
        """
        Prep the module files for OpenTofu.
        """
        cloud = config["cloud"]
        role = config["k3s_role"]
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        templates_dir = os.path.join(base_dir, "templates")
        config["module_source"] = f"{templates_dir}/{cloud}/"

        # Generate a cluster name if not provided
        if "cluster_name" not in config:
            cluster_name = self.generate_random_name()
            config["cluster_name"] = cluster_name

        cluster_dir = self.get_cluster_output_dir(config["cluster_name"])
        
        random_name = self.generate_random_name()
        config["resource_name"] = f"{cloud}_{random_name}"

        main_tf_path = os.path.join(cluster_dir, "main.tf")
        backend_tf_path = os.path.join(cluster_dir, "backend.tf")
        os.makedirs(os.path.dirname(main_tf_path), exist_ok=True)

        user_data_src = os.path.join(templates_dir, f"{role}_user_data.sh.tpl")
        user_data_dst = os.path.join(templates_dir, cloud, f"{role}_user_data.sh.tpl")
        shutil.copy2(user_data_src, user_data_dst)

        conn_str = (
            f"postgres://{self.pg_config['user']}:"
            f"{self.pg_config['password']}@"
            f"{self.pg_config['host']}:5432/"
            f"{self.pg_config['database']}?"
            f"sslmode={self.pg_config['sslmode']}"
        )
        config["pg_conn_str"] = conn_str  # Add the connection string to the config
        hcl.add_backend_config(backend_tf_path, conn_str, config["cluster_name"])

        target = f"{cloud}_{random_name}"
    
        hcl.add_module_block(main_tf_path, target, config)
        self.deploy(cluster_dir)


    def deploy(self, cluster_dir, dryrun=False):
        """
        Execute OpenTofu commands to deploy the K3s component with error handling.
        """
        try:
            print(f"Initializing OpenTofu...")
            subprocess.run(["tofu", "init"], check=True, cwd=cluster_dir)
            
            print(f"Planning infrastructure...")
            subprocess.run(["tofu", "plan"], check=True, cwd=cluster_dir)
            
            print(f"Applying infrastructure...")
            subprocess.run(["tofu", "apply", "-auto-approve"], check=True, cwd=cluster_dir)
            
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
            return

        except Exception as e:
            print(f"An unexpected error occurred during destruction of cluster '{cluster_name}': {e}")
            return
        
        shutil.rmtree(cluster_dir, ignore_errors=True)