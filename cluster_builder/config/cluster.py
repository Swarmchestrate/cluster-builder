"""
Cluster configuration management.
"""

import os
import logging

from names_generator import generate_name

from cluster_builder.templates.manager import TemplateManager

logger = logging.getLogger("swarmchestrate")


class ClusterConfig:
    """Manages cluster configuration and preparation."""

    def __init__(
        self,
        template_manager: TemplateManager,
        output_dir: str,
    ):
        """
        Initialise the ClusterConfig.

        Args:
            template_manager: Template manager instance
            output_dir: Directory for output files
        """
        self.template_manager = template_manager
        self.output_dir = output_dir

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

    def prepare(self, config: dict[str, any]) -> tuple[str, dict[str, any]]:
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

        return cluster_dir, prepared_config
