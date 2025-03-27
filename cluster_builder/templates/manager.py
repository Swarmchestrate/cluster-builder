"""
Template management for cluster deployments.
"""

import os
import shutil
import logging

import jinja2

from cluster_builder.config.cloud import CloudConfigLoader

logger = logging.getLogger("swarmchestrate")


class TemplateManager:
    """Manages template files and operations for cluster deployment."""

    def __init__(self):
        """Initialise the TemplateManager."""
        current_dir = os.path.dirname(os.path.abspath(__file__))  # templates directory
        self.base_dir = os.path.dirname(
            os.path.dirname(current_dir)
        )  # Go up two levels
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
            RuntimeError: If provider configuration cannot be created
            ValueError: If provider template is not found
        """
        # Load cloud-specific configuration from environment
        try:
            config = CloudConfigLoader.load(cloud)
        except ValueError as e:
            logger.error(f"Cloud configuration error: {e}")
            raise

        provider_file = os.path.join(cluster_dir, f"{cloud.lower()}_provider.tf")

        # Define the path for provider templates in the templates/ directory
        provider_template_path = os.path.join(
            self.templates_dir, f"{cloud.lower()}_provider.tf.j2"
        )

        # Check if template exists
        if not os.path.exists(provider_template_path):
            error_msg = f"Provider template not found: {provider_template_path}"
            logger.error(error_msg)
            raise ValueError(
                f"Provider template for cloud '{cloud}' not found. Expected at: {provider_template_path}"
            )

        try:
            # Set up Jinja2 environment
            template_loader = jinja2.FileSystemLoader(
                os.path.dirname(provider_template_path)
            )
            template_env = jinja2.Environment(loader=template_loader)

            # Get the template
            template = template_env.get_template(
                os.path.basename(provider_template_path)
            )

            # Render the template with the configuration
            content = template.render(**config)

            # Write the provider configuration
            with open(provider_file, "w") as f:
                f.write(content)

            logger.info(f"Created {cloud} provider configuration at {provider_file}")

        except jinja2.exceptions.TemplateError as e:
            error_msg = f"Template error creating provider configuration: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
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
