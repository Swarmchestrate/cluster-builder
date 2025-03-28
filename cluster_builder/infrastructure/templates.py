"""
Template management for cluster deployments.
"""

import os
import shutil
import logging

from cluster_builder.utils.hcl import extract_template_variables

logger = logging.getLogger("swarmchestrate")


class TemplateManager:
    """Manages template files and operations for cluster deployment."""

    def __init__(self):
        """Initialise the TemplateManager."""
        current_dir = os.path.dirname(os.path.abspath(__file__))  
        self.base_dir = os.path.dirname(current_dir) # templates directory
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

    def create_provider_config(self, cluster_dir: str, cloud: str) -> None:
        """
        Create provider configuration file for a specific cloud provider.

        Args:
            cluster_dir: Directory for the cluster
            cloud: Cloud provider (e.g., 'aws')

        Raises:
            ValueError: If provider template is not found
        """
        # Define the path for provider config in templates directory
        provider_template_path = os.path.join(
            self.templates_dir, f"{cloud.lower()}_provider.tf"
        )

        # Check if template exists
        if not os.path.exists(provider_template_path):
            error_msg = f"Provider template not found: {provider_template_path}"
            logger.error(error_msg)
            raise ValueError(
                f"Provider template for cloud '{cloud}' not found. Expected at: {provider_template_path}"
            )

        # Target file in cluster directory
        provider_file = os.path.join(cluster_dir, f"{cloud.lower()}_provider.tf")

        try:
            # Simply copy the provider config file to the cluster directory
            shutil.copy2(provider_template_path, provider_file)
            logger.info(f"Created {cloud} provider configuration at {provider_file}")
        except Exception as e:
            error_msg = f"Failed to create provider configuration: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

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

    def get_required_variables(self, cloud: str) -> dict:
        """
        Get the variables required for a specific cloud provider's templates.

        Args:
            cloud: Cloud provider name (e.g., 'aws')

        Returns:
            Dictionary of variable names to their configurations
        """
        template_path = os.path.join(self.templates_dir, cloud, "main.tf")
        return extract_template_variables(template_path)
