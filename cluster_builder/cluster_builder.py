import os
import subprocess
import shutil
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from names_generator import generate_name

from cluster_builder.utils import hcl

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("swarmchestrate")


@dataclass
class PostgresConfig:
    """Configuration for PostgreSQL backend."""

    user: str
    password: str
    host: str
    database: str
    sslmode: str = "prefer"

    @classmethod
    def from_dict(cls, config: Dict[str, str]) -> "PostgresConfig":
        """
        Create a PostgresConfig instance from a dictionary.

        Args:
            config: Dictionary containing PostgreSQL configuration

        Returns:
            PostgresConfig instance

        Raises:
            ValueError: If required configuration is missing
        """
        required_keys = ["user", "password", "host", "database"]
        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
            raise ValueError(
                f"Missing required PostgreSQL configuration: {', '.join(missing_keys)}"
            )

        return cls(
            user=config["user"],
            password=config["password"],
            host=config["host"],
            database=config["database"],
            sslmode=config.get("sslmode", "prefer"),
        )

    def get_connection_string(self) -> str:
        """Generate a PostgreSQL connection string from the configuration."""
        return (
            f"postgres://{self.user}:{self.password}@"
            f"{self.host}:5432/{self.database}?"
            f"sslmode={self.sslmode}"
        )


class CommandExecutor:
    """Utility for executing shell commands with proper logging and error handling."""

    @staticmethod
    def run_command(command: list, cwd: str, description: str = "command") -> str:
        """
        Execute a shell command with proper logging and error handling.

        Args:
            command: List containing the command and its arguments
            cwd: Working directory for the command
            description: Description of the command for logging

        Returns:
            Command stdout output as string

        Raises:
            RuntimeError: If the command execution fails
        """
        cmd_str = " ".join(command)
        logger.info(f"Running {description}: {cmd_str}")

        try:
            result = subprocess.run(
                command,
                check=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.debug(f"{description.capitalize()} output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = f"Error executing {description}: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during {description}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)


class Swarmchestrate:
    def __init__(
        self,
        template_dir: str,
        output_dir: str,
        pg_config: Dict[str, str],
        variables: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialise the Swarmchestrate class.

        Args:
            template_dir: Directory containing templates
            output_dir: Directory for outputting generated files
            pg_config: PostgreSQL configuration dictionary
            variables: Optional additional variables for deployments
        """
        self.template_dir = f"{template_dir}"
        self.output_dir = output_dir

        try:
            self.pg_config = PostgresConfig.from_dict(pg_config)
        except ValueError as e:
            logger.error(f"Invalid PostgreSQL configuration: {e}")
            raise

        logger.info(
            f"Initialised with template_dir={template_dir}, output_dir={output_dir}"
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
            # Use PostgresConfig to generate connection string
            conn_str = self.pg_config.get_connection_string()
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
            # Initialise OpenTofu
            init_command = ["tofu", "init"]
            if dryrun:
                logger.info("Dryrun: will init without backend and validate only")
                init_command.append("-backend=false")
            CommandExecutor.run_command(init_command, cluster_dir, "OpenTofu init")

            # Validate the deployment
            if dryrun:
                CommandExecutor.run_command(
                    ["tofu", "validate"], cluster_dir, "OpenTofu validate"    
                )
                logger.info("Infrastructure successfully validated")
                return 
            
            # Plan the deployment
            CommandExecutor.run_command(["tofu", "plan"], cluster_dir, "OpenTofu plan")

            # Apply the deployment
            CommandExecutor.run_command(
                ["tofu", "apply", "-auto-approve"], cluster_dir, "OpenTofu apply"
            )
            logger.info("Infrastructure successfully deployed")

        except RuntimeError as e:
            error_msg = f"Failed to deploy infrastructure: {str(e)}"
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
            # Plan destruction
            CommandExecutor.run_command(
                ["tofu", "plan", "-destroy"], cluster_dir, "OpenTofu plan destruction"
            )

            # Execute destruction
            CommandExecutor.run_command(
                ["tofu", "destroy", "-auto-approve"], cluster_dir, "OpenTofu destroy"
            )

            logger.info(f"Cluster '{cluster_name}' destroyed successfully")

            # Remove the cluster directory
            shutil.rmtree(cluster_dir, ignore_errors=True)
            logger.info(f"Removed cluster directory: {cluster_dir}")

        except RuntimeError as e:
            error_msg = f"Failed to destroy cluster '{cluster_name}': {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
