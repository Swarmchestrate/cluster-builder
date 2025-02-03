# import time
import jinja2
import os
import subprocess

class Swarmchestrate:
    def __init__(self, template_dir, output_dir,tfvars_file=None, variables=None):
        """
        Initialize the K3sCluster class.

        """
        self.template_dir = f"{template_dir}"
        self.output_dir = output_dir
        

    def create(self, config):
        """
        Create a new K3s cluster with OpenTofu.
        """
        print("Creating K3s cluster...")

        self.deploy_k3s_master(config)

        # self.deploy_k3s_ha(config)
        # self.deploy_k3s_worker()


    def generate_main_tf(self, config):
        """
        Dynamically generate main.tf based on the configuration.
        """
        main_tf_content = """
module "k3s_master" {
  source = "./k3s_master"
}
"""

        if config.get("aws_ha_server_count", 0) > 0:
            main_tf_content += """
module "k3s_ha" {
  source = "./k3s_ha"
  master_ip         = module.k3s_master.master_ip
  cluster_name      = module.k3s_master.cluster_name
  security_group_id = module.k3s_master.security_group_id
}
"""

        if config.get("aws_worker_count", 0) > 0:
            main_tf_content += """
module "k3s_worker" {
  source = "./k3s_worker"
  master_ip         = module.k3s_master.master_ip
  cluster_name      = module.k3s_master.cluster_name
  security_group_id = module.k3s_master.security_group_id
}
"""

        # Only write main.tf if at least one module is included
        if main_tf_content.strip():
            with open(os.path.join(self.output_dir, "main.tf"), "w") as f:
                f.write(main_tf_content.strip())

            print("Generated main.tf dynamically.")


    def substitute_values(self, config, subdir=None):
        """
        Substitute values into Jinja2 templates and save the rendered files.
        """
        out_dir = f"{self.output_dir}/{subdir if subdir else ''}"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        cloud_template_dir = f"{self.template_dir}/{config['cloud']}"
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(cloud_template_dir))
        
        for template_name in os.listdir(cloud_template_dir):
            if subdir and "master" not in subdir and "network_security" in template_name:
                continue
            if template_name.endswith('.j2'):
                template = env.get_template(template_name)
                rendered_content = template.render(config)
                output_path = os.path.join(out_dir, template_name[:-3])  

                with open(output_path, 'w') as f:
                    f.write(rendered_content)
                print(f"Rendered template saved to: {output_path}")
        
        self.generate_main_tf(config)
        #copy main.tf to output directory
        # main_tf_path = f"{self.template_dir}/main.tf"
        # if os.path.exists(main_tf_path):
        #     subprocess.run(["cp", main_tf_path, self.output_dir], check=True)
        #     print(f"Copied main.tf to {self.output_dir}")
        # else:
        #     print(f"Warning: main.tf not found in {self.template_dir}. Skipping copy.")


    def deploy_k3s_master(self, config):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        config["k3s_role"] = "master"
        self.substitute_values(config, "k3s_master")
        
        print("Initializing OpenTofu...")
        subprocess.run(["tofu", "init"], check=True, cwd=self.output_dir)
        print("Planning infrastructure with OpenTofu...")
        subprocess.run(["tofu", "plan", "-target=module.k3s_master"], check=True, cwd=self.output_dir)
        print("Applying infrastructure with OpenTofu...")
        subprocess.run(["tofu", "apply", "-auto-approve", "-target=module.k3s_master"], check=True, cwd=self.output_dir)
       

    def deploy_k3s_ha(self, config):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        config["k3s_role"] = "ha"
        self.substitute_values(config, "k3s_ha")

        print("Initializing OpenTofu...")
        subprocess.run(["tofu", "init"], check=True, cwd=self.output_dir)
        print("Planning infrastructure with OpenTofu...")
        subprocess.run(["tofu", "plan", "-target=module.k3s_ha"], check=True, cwd=self.output_dir)
        print("Applying infrastructure with OpenTofu...")
        subprocess.run(["tofu", "apply", "-auto-approve", "-target=module.k3s_ha"], check=True, cwd=self.output_dir)

#

    def deploy_k3s_worker(self, config):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        config["k3s_role"] = "worker"
        self.substitute_values(config, "k3s_worker")

        print("Initializing OpenTofu...")
        subprocess.run(["tofu", "init"], check=True, cwd=self.output_dir)
        print("Planning infrastructure with OpenTofu...")
        subprocess.run(["tofu", "plan", "-target=module.k3s_worker_one"], check=True, cwd=self.output_dir)
        print("Applying infrastructure with OpenTofu...")
        subprocess.run(["tofu", "apply", "-auto-approve", "-target=module.k3s_worker_one"], check=True, cwd=self.output_dir)

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

config = {
    "aws_region": "eu-west-2",   # London region
    "instance_type": "t2.micro",
    "ssh_key_name": "g",           # AWS key pair name  
    "k3s_token": "test",
    "ami": "ami-0c0493bbac867d427",
    "aws_ha_server_count": 0,
    "aws_worker_count": 0,
    "cloud": "aws"
}

swarmchestrate.create(config)

# delay_seconds = 5 * 60
# print(f"Waiting for {delay_seconds / 60} minutes before destroying resources...")
# time.sleep(delay_seconds)

# print("Starting the destruction process...")
# swarmchestrate.destroy()