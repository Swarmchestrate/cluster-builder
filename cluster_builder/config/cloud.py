"""
Cloud Auth Configuration Loader
"""

import os
import logging
from typing import Dict, Callable

logger = logging.getLogger("swarmchestrate")


class CloudConfigLoader:
    """
    Dynamically manage cloud provider configurations.
    """

    _config_loaders: Dict[str, Callable[[str], dict]] = {}

    @classmethod
    def register(cls, provider: str, loader_func: Callable[[str], dict]):
        """
        Register a configuration loader for a specific cloud provider.

        Args:
            provider: Lowercase cloud provider name
            loader_func: Function that returns a configuration dictionary
        """
        cls._config_loaders[provider.lower()] = loader_func

    @classmethod
    def load(cls, cloud: str) -> dict:
        """
        Load cloud-specific configuration from environment variables.

        Args:
            cloud: Cloud provider name

        Returns:
            Dictionary of cloud configuration

        Raises:
            ValueError: If cloud provider is not registered
        """
        cloud = cloud.lower()

        if cloud not in cls._config_loaders:
            raise ValueError(
                f"No configuration loader registered for cloud provider: {cloud}"
            )

        return cls._config_loaders[cloud]()


# Default cloud configuration loaders
def aws_config_loader() -> dict:
    """
    Load AWS-specific configuration from environment variables.
    """
    return {
        "aws_region": os.environ.get("AWS_REGION"),
        "aws_access_key": os.environ.get("AWS_ACCESS_KEY"),
        "aws_secret_key": os.environ.get("AWS_SECRET_KEY"),
    }


# Register cloud providers
CloudConfigLoader.register("aws", aws_config_loader)
