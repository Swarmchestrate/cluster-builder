import os
import subprocess
import shutil
import logging
from typing import Dict, Any, Optional, Tuple
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


class TemplateManager:
    """Manages template files and operations for cluster deployment."""

    def __init__(self):
        """Initialise the TemplateManager."""
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.templates_dir = os.path.join(self.base_dir, "templates")
        logger.debug(
            f"Initialised TemplateManager with templates_dir={self.templates_dir}"
        )

    def get_module_source_path(self, cloud: str) -> str:
        """
        Get the module source path for a specific cloud provider.

        Args:
            cloud: Cloud provider name

        Returns:
            Path to the module source directory
        """
        return f"{self.templates_dir}/{cloud}/"

    def copy_user_data_template(self, role: str, cloud: str) -> None:
        """
        Copy the user data template for a specific role to the cloud provider directory.

        Args:
            role: K3s role (master, worker, etc.)
            cloud: Cloud provider name

        Raises:
            RuntimeError: If the template file doesn't exist or can't be copied
        """
        user_data_src = os.path.join(self.templates_dir, f"{role}_user_data.sh.tpl")
        user_data_dst = os.path.join(
            self.templates_dir, cloud, f"{role}_user_data.sh.tpl"
        )

        if not os.path.exists(user_data_src):
            error_msg = f"User data template not found: {user_data_src}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            shutil.copy2(user_data_src, user_data_dst)
            logger.info(
                f"Copied user data template from {user_data_src} to {user_data_dst}"
            )
        except (OSError, shutil.Error) as e:
            error_msg = f"Failed to copy user data template: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)


class ClusterConfig:
    """Manages cluster configuration and preparation."""

    def __init__(
        self,
        template_manager: TemplateManager,
        output_dir: str,
        pg_config: PostgresConfig,
    ):
        """
        Initialise the ClusterConfig.

        Args:
            template_manager: Template manager instance
            output_dir: Directory for output files
            pg_config: PostgreSQL configuration
        """
        self.template_manager = template_manager
        self.output_dir = output_dir
        self.pg_config = pg_config

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

    def prepare(self, config: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Prepare the configuration and template files for deployment.

        Args:
            config: Configuration dictionary containing cloud, k3s_role, and
                   optionally cluster_name

        Returns:
            Tuple containing the cluster directory path and updated configuration

        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If file operations fail
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

        # Create a copy of the configuration
        prepared_config = config.copy()

        cloud = prepared_config["cloud"]
        role = prepared_config["k3s_role"]
        logger.info(f"Preparing configuration for cloud={cloud}, role={role}")

        # Set module source path
        prepared_config["module_source"] = self.template_manager.get_module_source_path(
            cloud
        )
        logger.debug(f"Using module source: {prepared_config['module_source']}")

        # Generate a cluster name if not provided
        if "cluster_name" not in prepared_config:
            cluster_name = self.generate_random_name()
            prepared_config["cluster_name"] = cluster_name
            logger.info(f"Generated cluster name: {cluster_name}")
        else:
            logger.info(
                f"Using provided cluster name: {prepared_config['cluster_name']}"
            )

        cluster_dir = self.get_cluster_output_dir(prepared_config["cluster_name"])
        logger.debug(f"Cluster directory: {cluster_dir}")

        # Generate a resource name
        random_name = self.generate_random_name()
        prepared_config["resource_name"] = f"{cloud}_{random_name}"
        logger.debug(f"Resource name: {prepared_config['resource_name']}")

        # Create the cluster directory
        try:
            os.makedirs(cluster_dir, exist_ok=True)
            logger.debug(f"Created directory: {cluster_dir}")
        except OSError as e:
            error_msg = f"Failed to create directory {cluster_dir}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Copy user data template
        self.template_manager.copy_user_data_template(role, cloud)

        # Add PostgreSQL connection string to config
        conn_str = self.pg_config.get_connection_string()
        prepared_config["pg_conn_str"] = conn_str

        return cluster_dir, prepared_config


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

        # Initialise components
        self.template_manager = TemplateManager()
        self.cluster_config = ClusterConfig(
            self.template_manager, output_dir, self.pg_config
        )

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
        return self.cluster_config.get_cluster_output_dir(cluster_name)

    def generate_random_name(self) -> str:
        """
        Generate a readable random string using names-generator.

        Returns:
            A randomly generated name
        """
        return self.cluster_config.generate_random_name()

    def prepare_cluster(self, config: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Prepare a cluster configuration for deployment.

        This method prepares the necessary files and configuration for deployment
        but does not actually deploy the infrastructure.

        Args:
            config: Configuration dictionary containing cloud, k3s_role, and
                   optionally cluster_name

        Returns:
            Tuple containing the cluster directory path and updated configuration

        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If file operations fail
        """
        try:
            # Prepare the configuration and files
            cluster_dir, prepared_config = self.cluster_config.prepare(config)

            # Create Terraform files
            main_tf_path = os.path.join(cluster_dir, "main.tf")
            backend_tf_path = os.path.join(cluster_dir, "backend.tf")

            # Add backend configuration
            hcl.add_backend_config(
                backend_tf_path,
                prepared_config["pg_conn_str"],
                prepared_config["cluster_name"],
            )
            logger.info(f"Added backend configuration to {backend_tf_path}")

            # Add module block
            target = prepared_config["resource_name"]
            hcl.add_module_block(main_tf_path, target, prepared_config)
            logger.info(f"Added module block to {main_tf_path}")

            return cluster_dir, prepared_config

        except Exception as e:
            error_msg = f"Failed to prepare cluster: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def create_cluster(self, config: Dict[str, Any], dryrun: bool = False) -> str:
        """
        Create a new cluster with the given configuration.

        This method prepares the configuration and then deploys the infrastructure.

        Args:
            config: Configuration dictionary containing cloud, k3s_role, and
                   optionally cluster_name
            dryrun: If True, only validate the configuration without deploying

        Returns:
            The name of the created cluster

        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If preparation or deployment fails
        """
        # Prepare the cluster
        cluster_dir, prepared_config = self.prepare_cluster(config)

        # Deploy the infrastructure
        try:
            self.deploy(cluster_dir, dryrun)
            cluster_name = prepared_config["cluster_name"]
            logger.info(f"Successfully created cluster '{cluster_name}'")
            return cluster_name
        except Exception as e:
            error_msg = f"Failed to create cluster: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def prepare_modules(self, config: Dict[str, Any]) -> None:
        """
        Prepare the module files for OpenTofu and deploy (legacy method).

        Args:
            config: Configuration dictionary containing cloud, k3s_role, and
                   optionally cluster_name

        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If file operations or OpenTofu commands fail
        """
        logger.warning("prepare_modules() is deprecated, use create_cluster() instead")
        self.create_cluster(config)

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
