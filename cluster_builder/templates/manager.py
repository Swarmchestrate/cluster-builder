"""
Template management for cluster deployments.
"""

import os
import shutil
import logging

logger = logging.getLogger("swarmchestrate")


class TemplateManager:
    """Manages template files and operations for cluster deployment."""

    def __init__(self):
        """Initialise the TemplateManager."""
        current_dir = os.path.dirname(os.path.abspath(__file__))  # templates directory
        self.base_dir = os.path.dirname(os.path.dirname(current_dir))  # Go up two levels
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
