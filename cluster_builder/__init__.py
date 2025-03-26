"""
Cluster Builder - A tool for creating, managing, and destroying K3s clusters.
"""

import logging
import sys

# Configure logging at package import time
def _configure_package_logging():
    """Internal function to configure logging when package is imported."""
    # Root logger configuration
    root_logger = logging.getLogger()
    
    # Only configure if no handlers exist (avoid duplicate configuration)
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Configure swarmchestrate logger
        logger = logging.getLogger("swarmchestrate")
        logger.setLevel(logging.INFO)

# Run the configuration
_configure_package_logging()

# Import and re-export the Swarmchestrate class
from cluster_builder.swarmchestrate import Swarmchestrate

# Export the class
__all__ = ['Swarmchestrate']