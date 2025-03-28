"""
Swarmchestrate - Main orchestration class for K3s cluster management.
"""

import os
import logging
import shutil
from typing import Optional

from dotenv import load_dotenv

from cluster_builder.config.postgres import PostgresConfig
from cluster_builder.config.cluster import ClusterConfig
from cluster_builder.infrastructure import TemplateManager
from cluster_builder.infrastructure import CommandExecutor
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
        variables: Optional[dict[str, any]] = None,
    ):
        """
        Initialise the Swarmchestrate class.

        Args:
            template_dir: Directory containing templates
            output_dir: Directory for outputting generated files
            variables: Optional additional variables for deployments
        """
        self.template_dir = f"{template_dir}"
        self.output_dir = output_dir

        load_dotenv()

        try:
            self.pg_config = PostgresConfig.from_env()
        except ValueError as e:
            logger.error(f"Invalid PostgreSQL configuration: {e}")
            raise

        # Initialise components
        self.template_manager = TemplateManager()
        self.cluster_config = ClusterConfig(self.template_manager, output_dir)

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

    def validate_configuration(self, cloud: str, config: dict) -> list:
        """
        Validate a configuration against the required variables for a cloud provider.

        Args:
            cloud: Cloud provider name
            config: Configuration dictionary provided by the user

        Returns:
            List of missing required variables (empty if all required variables are present)
        """
        # Master IP validation
        has_master_ip = "master_ip" in config and config["master_ip"]
        role = config["k3s_role"]

        # Cannot add a master node to an existing cluster
        if has_master_ip and role == "master":
            raise ValueError(
                "Cannot add master to existing cluster (master_ip specified with master role)"
            )

        # Worker/HA nodes require a master IP
        if not has_master_ip and role in ["worker", "ha"]:
            raise ValueError(f"Role '{role}' requires master_ip to be specified")

        required_vars = self.template_manager.get_required_variables(cloud)

        # Find missing required variables
        missing_vars = []
        for var_name, var_config in required_vars.items():
            # If variable has no default and is not in config, it's required but missing
            if "default" not in var_config and var_name not in config:
                missing_vars.append(var_name)

        return missing_vars

    def prepare_infrastructure(
        self, config: dict[str, any]
    ) -> tuple[str, dict[str, any]]:
        """
        Prepare infrastructure configuration for deployment.

        This method prepares the necessary files and configuration for deployment
        but does not actually deploy the infrastructure.

        Args:
            config: Configuration dictionary containing cloud, k3s_role, and
                optionally cluster_name and master_ip

        Returns:
            Tuple containing the cluster directory path and updated configuration

        Raises:
            ValueError: If required configuration is missing or invalid
            RuntimeError: If file operations fail
        """
        try:
            # Prepare the configuration
            cluster_dir, prepared_config = self.cluster_config.prepare(config)

            # Validate the configuration
            cloud = prepared_config["cloud"]
            missing_vars = self.validate_configuration(cloud, prepared_config)
            if missing_vars:
                raise ValueError(
                    f"Missing required variables for cloud provider '{cloud}': {', '.join(missing_vars)}"
                )

            # Create provider configuration
            self.template_manager.create_provider_config(cluster_dir, cloud)
            logger.info(f"Created provider configuration for {cloud}")

            # Create Terraform files
            main_tf_path = os.path.join(cluster_dir, "main.tf")
            backend_tf_path = os.path.join(cluster_dir, "backend.tf")

            # Add backend configuration

            # Add PostgreSQL connection string to config
            conn_str = self.pg_config.get_connection_string()
            hcl.add_backend_config(
                backend_tf_path,
                conn_str,
                prepared_config["cluster_name"],
            )
            logger.info(f"Added backend configuration to {backend_tf_path}")

            # Add module block
            target = prepared_config["resource_name"]
            hcl.add_module_block(main_tf_path, target, prepared_config)
            logger.info(f"Added module block to {main_tf_path}")

            return cluster_dir, prepared_config

        except Exception as e:
            error_msg = f"Failed to prepare infrastructure: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def add_node(self, config: dict[str, any], dryrun: bool = False) -> str:
        """
        Add a node to an existing cluster or create a new cluster based on configuration.

        If master_ip is provided, adds a node to that cluster.
        If master_ip is not provided, creates a new cluster.

        Args:
            config: Configuration dictionary containing cloud, k3s_role, and
                   optionally cluster_name and master_ip
            dryrun: If True, only validate the configuration without deploying

        Returns:
            The cluster name

        Raises:
            ValueError: If required configuration is missing or invalid
            RuntimeError: If preparation or deployment fails
        """
        # Prepare the infrastructure configuration
        cluster_dir, prepared_config = self.prepare_infrastructure(config)

        logger.info(f"Adding node for cluster '{prepared_config['cluster_name']}'")

        # Deploy the infrastructure
        try:
            self.deploy(cluster_dir, dryrun)
            cluster_name = prepared_config["cluster_name"]
            node_name = prepared_config["resource_name"]
            logger.info(
                f"Successfully added '{node_name}' for cluster '{cluster_name}'"
            )
            return cluster_name
        except Exception as e:
            error_msg = f"Failed to add node: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def remove_node(
        self, cluster_name: str, resource_name: str, dryrun: bool = False
    ) -> None:
        """
        Remove a specific node from a cluster.

        This method removes a node's infrastructure component from a cluster by
        removing its module block from the Terraform configuration and then
        reapplying the configuration.

        Args:
            cluster_name: Name of the cluster containing the node
            resource_name: Resource name of the node to remove
            dryrun: If True, only validate the changes without applying

        Raises:
            RuntimeError: If node removal fails
        """
        logger.info(f"Removing node '{resource_name}' from cluster '{cluster_name}'...")

        # Get the directory for the specified cluster
        cluster_dir = self.get_cluster_output_dir(cluster_name)

        if not os.path.exists(cluster_dir):
            error_msg = f"Cluster directory '{cluster_dir}' not found"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Path to main.tf
        main_tf_path = os.path.join(cluster_dir, "main.tf")

        if not os.path.exists(main_tf_path):
            error_msg = f"Main Terraform file not found: {main_tf_path}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            # Remove the module block for the specified resource
            hcl.remove_module_block(main_tf_path, resource_name)
            logger.info(
                f"Removed module block for '{resource_name}' from {main_tf_path}"
            )

            self.deploy(cluster_dir, dryrun)

            if not dryrun:
                logger.info(
                    f"Successfully removed node '{resource_name}' from cluster '{cluster_name}'"
                )

        except Exception as e:
            error_msg = f"Failed to remove node '{resource_name}' from cluster '{cluster_name}': {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def deploy(self, cluster_dir: str, dryrun: bool = False) -> None:
        """
        Execute OpenTofu commands to deploy the K3s component with error handling.

        Args:
            cluster_dir: Directory containing the Terraform files for the cluster
            dryrun: If True, only run init and plan without applying

        Raises:
            RuntimeError: If OpenTofu commands fail
        """
        logger.info(f"Updating infrastructure in {cluster_dir}")

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
            CommandExecutor.run_command(
                ["tofu", "plan", "-input=false"],
                cluster_dir,
                "OpenTofu plan",
                timeout=30,
            )

            # Apply the deployment
            CommandExecutor.run_command(
                ["tofu", "apply", "-auto-approve"], cluster_dir, "OpenTofu apply"
            )
            logger.info("Infrastructure successfully updated")

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
                ["tofu", "plan", "-destroy", "-input=false"],
                cluster_dir,
                "OpenTofu plan destruction",
                timeout=30,
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
