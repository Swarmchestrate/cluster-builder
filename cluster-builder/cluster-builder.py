import time
import jinja2
import os
import subprocess
import hcl2
import re

class Swarmchestrate:
    def __init__(self, template_dir, output_dir,tfvars_file=None, variables=None):
        """
        Initialize the K3sCluster class.

        """
        self.template_dir = template_dir
        self.output_dir = output_dir
        if tfvars_file:
            self.variables = self.load_variables_from_tfvars(tfvars_file)
        else:
            self.variables = variables

    def load_variables_from_tfvars(self, tfvars_file):
        """
        Load variables from a .tfvars file.

        """
        with open(tfvars_file, 'r') as f:
            tfvars = hcl2.load(f)
        return tfvars

    def create(self):
        """
        Create a new K3s cluster with OpenTofu.
        """
        print("Creating K3s cluster...")
        self.substitute_values()
        self.deploy_k3s_master()
        self.deploy_k3s_ha()
        self.deploy_k3s_worker()

        # self.configure()

    def substitute_values(self):
        """
        Substitute values into Jinja2 templates and save the rendered files.
        """
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.template_dir))
        
        for template_name in os.listdir(self.template_dir):
            if template_name.endswith('.j2'):
                template = env.get_template(template_name)
                rendered_content = template.render(self.variables)
                output_path = os.path.join(self.output_dir, template_name[:-3])  

                with open(output_path, 'w') as f:
                    f.write(rendered_content)
                print(f"Rendered template saved to: {output_path}")

    def deploy_k3s_master(self):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        self.variables["k3s_role"] = "master"
        self.substitute_values()


        print("Initializing OpenTofu...")
        subprocess.run(["tofu", "init"], check=True, cwd=self.output_dir)
        print("Planning infrastructure with OpenTofu...")
        subprocess.run(["tofu", "plan", "-var-file=../terraform.tfvars"], check=True, cwd=self.output_dir)
        print("Applying infrastructure with OpenTofu...")
        subprocess.run(["tofu", "apply", "-auto-approve", "-var-file=../terraform.tfvars"], check=True, cwd=self.output_dir)
        print("Fetching cluster name and master node IP...")
    
        # Get cluster name
        cluster_name_result = subprocess.run(["tofu", "output", "-raw", "cluster_name"], capture_output=True, text=True, cwd=self.output_dir)
        cluster_name = cluster_name_result.stdout.strip() if cluster_name_result.returncode == 0 else None
    
        # Get master node IP
        master_ip_result = subprocess.run(["tofu", "output", "-raw", "master_ip"], capture_output=True, text=True, cwd=self.output_dir)
        master_ip = master_ip_result.stdout.strip() if master_ip_result.returncode == 0 else None

        if cluster_name and master_ip:
            print(f"Cluster Name: {cluster_name}")
            print(f"Master Node IP: {master_ip}")

            tfvars_path = f"{self.output_dir}/../terraform.tfvars"

            # Read the existing terraform.tfvars content
            try:
                with open(tfvars_path, "r") as f:
                    lines = f.readlines()
            except FileNotFoundError:
                lines = []

            # Update or add the variables
            def update_or_append(key, value):
                found = False
                for i, line in enumerate(lines):
                    if re.match(rf'^\s*{key}\s*=', line):
                        lines[i] = f'{key} = "{value}"\n'
                        found = True
                        break
                if not found:
                    lines.append(f'\n{key} = "{value}"\n')

            update_or_append("cluster_name", cluster_name)
            update_or_append("master_ip", master_ip)

            # Write back the modified file
            with open(tfvars_path, "w") as f:
                f.writelines(lines)

            print("Cluster name and master IP saved successfully in terraform.tfvars.")
        else:
            print("Failed to fetch cluster name or master IP. Check OpenTofu outputs.")


    def deploy_k3s_ha(self):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        self.variables["k3s_role"] = "ha"
        self.substitute_values()

        print("Initializing OpenTofu...")
        subprocess.run(["tofu", "init"], check=True, cwd=self.output_dir)
        print("Planning infrastructure with OpenTofu...")
        subprocess.run(["tofu", "plan", "-var-file=../terraform.tfvars", ], check=True, cwd=self.output_dir)
        print("Applying infrastructure with OpenTofu...")
        subprocess.run(["tofu", "apply", "-auto-approve", "-var-file=../terraform.tfvars"], check=True, cwd=self.output_dir)

#

    def deploy_k3s_worker(self):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        self.variables["k3s_role"] = "worker"
        self.substitute_values()

        print("Initializing OpenTofu...")
        subprocess.run(["tofu", "init"], check=True, cwd=self.output_dir)
        print("Planning infrastructure with OpenTofu...")
        subprocess.run(["tofu", "plan", "-var-file=../terraform.tfvars"], check=True, cwd=self.output_dir)
        print("Applying infrastructure with OpenTofu...")
        subprocess.run(["tofu", "apply", "-auto-approve", "-var-file=../terraform.tfvars"], check=True, cwd=self.output_dir)

    def configure(self):
        """
        Configure the deployed K3s cluster ( for now it is covered in deploy step).
        """
        raise NotImplementedError

    def destroy(self):
        """
        Destroy the deployed K3s cluster using OpenTofu.
        """
        print("Destroying the K3s cluster...")
        try:
            print("Planning destruction with OpenTofu...")
            subprocess.run(["tofu", "plan", "-destroy"], check=True, cwd=self.output_dir)
            print("Destroying infrastructure with OpenTofu...")
            subprocess.run(["tofu", "destroy", "-auto-approve"], check=True, cwd=self.output_dir)
            print("K3s cluster destroyed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error during destruction: {e}")

swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output", tfvars_file="terraform.tfvars")
swarmchestrate.create()

# delay_seconds = 5 * 60
# print(f"Waiting for {delay_seconds / 60} minutes before destroying resources...")
# time.sleep(delay_seconds)

# print("Starting the destruction process...")
# swarmchestrate.destroy()