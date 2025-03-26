import os
import subprocess
import shutil
import logging
from typing import Dict, Any, Optional

from names_generator import generate_name

from cluster_builder.utils import hcl

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("swarmchestrate")


class Swarmchestrate:
    def __init__(
        self,
        template_dir: str,
        output_dir: str,
        pg_config: Dict[str, str],
        variables: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Swarmchestrate class.

        Args:
            template_dir: Directory containing templates
            output_dir: Directory for outputting generated files
            pg_config: PostgreSQL configuration dictionary
            variables: Optional additional variables for deployments
        """
        self.template_dir = f"{template_dir}"
        self.output_dir = output_dir
        self.pg_config = pg_config
        logger.info(
            f"Initialized Swarmchestrate with template_dir={template_dir}, output_dir={output_dir}"
        )

    def get_cluster_output_dir(self, cluster_name: str) -> str:
        """
        Get the output directory path for a specific cluster.

        Args:
            cluster_name: Name of the cluster

        Returns:
            Path to the cluster output directory
        """
        return os.path.join(self.output_dir, f"cluster_{cluster_name}")

    def generate_random_name(self) -> str:
        """
        Generate a readable random string using names-generator.

        Returns:
            A randomly generated name
        """
        name = generate_name()
        logger.debug(f"Generated random name: {name}")
        return name

    def prepare_modules(self, config: Dict[str, Any]) -> None:
        """
        Prepare the module files for OpenTofu.

        Args:
            config: Configuration dictionary containing cloud, k3s_role, and
                   optionally cluster_name

        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If file operations or OpenTofu commands fail
        """
        # Validate required configuration
        if "cloud" not in config:
            error_msg = "Cloud provider must be specified in configuration"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if "k3s_role" not in config:
            error_msg = "K3s role must be specified in configuration"
            logger.error(error_msg)
            raise ValueError(error_msg)

        cloud = config["cloud"]
        role = config["k3s_role"]
        logger.info(f"Preparing modules for cloud={cloud}, role={role}")

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        templates_dir = os.path.join(base_dir, "templates")
        config["module_source"] = f"{templates_dir}/{cloud}/"
        logger.debug(f"Using module source: {config['module_source']}")

        # Generate a cluster name if not provided
        if "cluster_name" not in config:
            cluster_name = self.generate_random_name()
            config["cluster_name"] = cluster_name
            logger.info(f"Generated cluster name: {cluster_name}")
        else:
            logger.info(f"Using provided cluster name: {config['cluster_name']}")

        cluster_dir = self.get_cluster_output_dir(config["cluster_name"])
        logger.debug(f"Cluster directory: {cluster_dir}")

        random_name = self.generate_random_name()
        config["resource_name"] = f"{cloud}_{random_name}"
        logger.debug(f"Resource name: {config['resource_name']}")

        main_tf_path = os.path.join(cluster_dir, "main.tf")
        backend_tf_path = os.path.join(cluster_dir, "backend.tf")

        try:
            os.makedirs(os.path.dirname(main_tf_path), exist_ok=True)
            logger.debug(f"Created directory: {os.path.dirname(main_tf_path)}")
        except OSError as e:
            error_msg = (
                f"Failed to create directory {os.path.dirname(main_tf_path)}: {e}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            user_data_src = os.path.join(templates_dir, f"{role}_user_data.sh.tpl")
            user_data_dst = os.path.join(
                templates_dir, cloud, f"{role}_user_data.sh.tpl"
            )

            if not os.path.exists(user_data_src):
                error_msg = f"User data template not found: {user_data_src}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            shutil.copy2(user_data_src, user_data_dst)
            logger.info(
                f"Copied user data template from {user_data_src} to {user_data_dst}"
            )
        except (OSError, shutil.Error) as e:
            error_msg = f"Failed to copy user data template: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            conn_str = (
                f"postgres://{self.pg_config['user']}:"
                f"{self.pg_config['password']}@"
                f"{self.pg_config['host']}:5432/"
                f"{self.pg_config['database']}?"
                f"sslmode={self.pg_config.get('sslmode', 'prefer')}"
            )
            config["pg_conn_str"] = conn_str

            hcl.add_backend_config(backend_tf_path, conn_str, config["cluster_name"])
            logger.info(f"Added backend configuration to {backend_tf_path}")

            target = f"{cloud}_{random_name}"
            hcl.add_module_block(main_tf_path, target, config)
            logger.info(f"Added module block to {main_tf_path}")
        except Exception as e:
            error_msg = f"Failed to create Terraform configuration: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            self.deploy(cluster_dir)
            logger.info(f"Successfully deployed cluster '{config['cluster_name']}'")
        except Exception as e:
            error_msg = f"Failed to deploy cluster: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def deploy(self, cluster_dir: str, dryrun: bool = False) -> None:
        """
        Execute OpenTofu commands to deploy the K3s component with error handling.

        Args:
            cluster_dir: Directory containing the Terraform files
            dryrun: If True, only run init and plan without applying

        Raises:
            RuntimeError: If OpenTofu commands fail
        """
        logger.info(f"Deploying infrastructure in {cluster_dir}")

        if not os.path.exists(cluster_dir):
            error_msg = f"Cluster directory '{cluster_dir}' not found"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            logger.info("Initializing OpenTofu...")
            result = subprocess.run(
                ["tofu", "init"],
                check=True,
                cwd=cluster_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.debug(f"OpenTofu init output: {result.stdout}")

            logger.info("Planning infrastructure...")
            result = subprocess.run(
                ["tofu", "plan"],
                check=True,
                cwd=cluster_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.debug(f"OpenTofu plan output: {result.stdout}")

            if not dryrun:
                logger.info("Applying infrastructure...")
                result = subprocess.run(
                    ["tofu", "apply", "-auto-approve"],
                    check=True,
                    cwd=cluster_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                logger.debug(f"OpenTofu apply output: {result.stdout}")
                logger.info("Infrastructure successfully deployed")

        except subprocess.CalledProcessError as e:
            error_msg = f"Error executing OpenTofu command: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during deployment: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def destroy(self, cluster_name: str) -> None:
        """
        Destroy the deployed K3s cluster for the specified cluster_name using OpenTofu.

        Args:
            cluster_name: Name of the cluster to destroy

        Raises:
            RuntimeError: If destruction fails
        """
        logger.info(f"Destroying the K3s cluster '{cluster_name}'...")

        # Get the directory for the specified cluster
        cluster_dir = self.get_cluster_output_dir(cluster_name)

        if not os.path.exists(cluster_dir):
            error_msg = f"Cluster directory '{cluster_dir}' not found"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            logger.info(f"Planning destruction for cluster '{cluster_name}'...")
            result = subprocess.run(
                ["tofu", "plan", "-destroy"],
                check=True,
                cwd=cluster_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.debug(f"OpenTofu plan destruction output: {result.stdout}")

            logger.info(f"Destroying infrastructure for cluster '{cluster_name}'...")
            result = subprocess.run(
                ["tofu", "destroy", "-auto-approve"],
                check=True,
                cwd=cluster_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.debug(f"OpenTofu destroy output: {result.stdout}")
            logger.info(f"Cluster '{cluster_name}' destroyed successfully")

            # Remove the cluster directory
            shutil.rmtree(cluster_dir, ignore_errors=True)
            logger.info(f"Removed cluster directory: {cluster_dir}")

        except subprocess.CalledProcessError as e:
            error_msg = (
                f"Error during destruction of cluster '{cluster_name}': {e.stderr}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"An unexpected error occurred during destruction of cluster '{cluster_name}': {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
