import jinja2
import os
import subprocess
import hcl

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
            tfvars = hcl.load(f)
        return tfvars

    def create(self):
        """
        Create a new K3s cluster with OpenTofu.
        """
        print("Creating K3s cluster...")
        self.substitute_values()
        self.deploy()
        self.configure()

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

    def deploy(self):
        """
        Deploy the K3s cluster using OpenTofu.
        """
        print("Initializing OpenTofu...")
        subprocess.run(["tofu", "init"], check=True)
        print("Planning infrastructure with OpenTofu...")
        subprocess.run(["tofu", "plan"], check=True)
        print("Applying infrastructure with OpenTofu...")
        subprocess.run(["tofu", "apply", "-auto-approve"], check=True)
  

    def configure(self):
        """
        Configure the deployed K3s cluster ( for now it is covered in deploy step).
        """
        raise NotImplementedError


swarmchestrate = Swarmchestrate(template_dir="templates", output_dir="output", tfvars_file="terraform.tfvars")
swarmchestrate.substitute_values()