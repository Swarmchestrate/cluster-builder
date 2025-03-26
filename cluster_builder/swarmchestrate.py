"""
Swarmchestrate - Main orchestration class for K3s cluster management.
"""

import os
import logging
import shutil
from typing import Optional

from cluster_builder.config.postgres import PostgresConfig
from cluster_builder.config.cluster import ClusterConfig
from cluster_builder.templates.manager import TemplateManager
from cluster_builder.infrastructure.executor import CommandExecutor
from cluster_builder.utils import hcl

logger = logging.getLogger("swarmchestrate")


class Swarmchestrate:
    """
    Main class for orchestrating K3s clusters across different cloud providers.
    """

    def __init__(
        self,
        template_dir: str,
        output_dir: str,
        pg_config: dict[str, str],
        variables: Optional[dict[str, any]] = None,
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

    def prepare_cluster(self, config: dict[str, any]) -> tuple[str, dict[str, any]]:
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

    def create_cluster(self, config: dict[str, any], dryrun: bool = False) -> str:
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

    def prepare_modules(self, config: dict[str, any], dryrun: bool = False) -> None:
        """
        Prepare the module files for OpenTofu and deploy (legacy method).

        Args:
            config: Configuration dictionary containing cloud, k3s_role, and
                   optionally cluster_name
            dryrun: Dryrun flag

        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If file operations or OpenTofu commands fail
        """
        logger.warning("prepare_modules() is deprecated, use create_cluster() instead")
        self.create_cluster(config, dryrun)

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

    def destroy(self, cluster_name: str, dryrun: bool = False) -> None:
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
        
        if dryrun:
            logger.info("Dryrun: will only delete")
            shutil.rmtree(cluster_dir, ignore_errors=True)
            return

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
