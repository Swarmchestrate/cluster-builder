"""
PostgreSQL configuration for Terraform state backend.
"""

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

    def get_connection_string(self) -> str:
        """Generate a PostgreSQL connection string from the configuration."""
        return (
            f"postgres://{self.user}:{self.password}@"
            f"{self.host}:5432/{self.database}?"
            f"sslmode={self.sslmode}"
        )
