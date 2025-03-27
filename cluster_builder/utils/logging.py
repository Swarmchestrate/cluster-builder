"""
Logging configuration for the cluster builder.
"""

import logging
import sys
from typing import Optional


def configure_logging(
    level: int = logging.INFO, log_file: Optional[str] = None
) -> None:
    """
    Configure or reconfigure logging for the cluster builder.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional path to log file
    """
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if log_file is provided)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure swarmchestrate logger
    logger = logging.getLogger("swarmchestrate")
    logger.setLevel(level)
