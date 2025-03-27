"""
PostgreSQL configuration for Terraform state backend.
"""

import os
import logging
from dataclasses import dataclass

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
    def from_dict(cls, config: dict[str, str]) -> "PostgresConfig":
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

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        """
        Create a PostgresConfig instance from environment variables.

        Environment variables used:
        - POSTGRES_USER
        - POSTGRES_PASSWORD
        - POSTGRES_HOST
        - POSTGRES_DATABASE
        - POSTGRES_SSLMODE (optional, defaults to 'prefer')

        Returns:
            PostgresConfig instance

        Raises:
            ValueError: If required environment variables are missing
        """
        # Check for required environment variables
        required_vars = [
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "POSTGRES_DATABASE",
        ]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]

        if missing_vars:
            raise ValueError(
                f"Missing required PostgreSQL environment variables: {', '.join(missing_vars)}"
            )

        # Create config from environment variables
        return cls(
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.environ["POSTGRES_HOST"],
            database=os.environ["POSTGRES_DATABASE"],
            sslmode=os.environ.get("POSTGRES_SSLMODE", "prefer"),
        )

    def get_connection_string(self) -> str:
        """Generate a PostgreSQL connection string from the configuration."""
        return (
            f"postgres://{self.user}:{self.password}@"
            f"{self.host}:5432/{self.database}?"
            f"sslmode={self.sslmode}"
        )
