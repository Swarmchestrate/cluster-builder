"""
Command execution utilities for infrastructure management.
"""

import subprocess
import logging

logger = logging.getLogger("swarmchestrate")


class CommandExecutor:
    """Utility for executing shell commands with proper logging and error handling."""

    @staticmethod
    def run_command(command: list, cwd: str, description: str = "command") -> str:
        """
        Execute a shell command with proper logging and error handling.

        Args:
            command: List containing the command and its arguments
            cwd: Working directory for the command
            description: Description of the command for logging

        Returns:
            Command stdout output as string

        Raises:
            RuntimeError: If the command execution fails
        """
        cmd_str = " ".join(command)
        logger.info(f"Running {description}: {cmd_str}")

        try:
            result = subprocess.run(
                command,
                check=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.debug(f"{description.capitalize()} output: {result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = f"Error executing {description}: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during {description}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
