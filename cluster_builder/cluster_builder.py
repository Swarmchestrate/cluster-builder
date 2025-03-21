import re
import jinja2
import os
import subprocess
from names_generator import generate_name

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
        conn_str = (
            f"postgres://{self.pg_config['user']}:"
            f"{self.pg_config['password']}@"
            f"{self.pg_config['host']}:5432/"
            f"{self.pg_config['database']}?"
            f"sslmode={self.pg_config['sslmode']}"
        )
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
        role = config["k3s_role"]
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        templates_dir = os.path.join(base_dir, "templates")
        config["module_source"] = f"{templates_dir}/{cloud}/"

        # Generate a cluster name if not provided
        if "cluster_name" not in config:
            cluster_name = self.generate_cluster_name()
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

        # Get the correct resource type for OpenTofu
        resource_type = self.get_target_resource(cloud)
        target = f"{resource_type}_{random_name}"
    
        hcl.add_module_block(main_tf_path, target, config)
        self.deploy(cluster_dir)
        os.remove(user_data_dst) if os.path.exists(user_data_dst) else None

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

        except Exception as e:
            print(f"An unexpected error occurred during destruction of cluster '{cluster_name}': {e}")
   
# swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output")

# swarmchestrate.deploy_k3s_master(aws_config)
#swarmchestrate.deploy_k3s_ha(aws_config)
#swarmchestrate.destroy("swarmchestrate_06z51q")
#swarmchestrate.deploy_k3s_ha(edge_config)
#swarmchestrate.deploy_k3s_master(aws_config)
#swarmchestrate.deploy_k3s_worker(aws_config)
