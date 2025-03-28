"""
Command execution utilities for infrastructure management.
"""

import subprocess
import logging

logger = logging.getLogger("swarmchestrate")


class CommandExecutor:
    """Utility for executing shell commands with proper logging and error handling."""

    @staticmethod
    def run_command(
        command: list, cwd: str, description: str = "command", timeout: int = None
    ) -> str:
        """
        Execute a shell command with proper logging and error handling.

        Args:
            command: List containing the command and its arguments
            cwd: Working directory for the command
            description: Description of the command for logging
            timeout: Maximum execution time in seconds (None for no timeout)

        Returns:
            Command stdout output as string

        Raises:
            RuntimeError: If the command execution fails or times out
        """
        cmd_str = " ".join(command)
        logger.info(f"Running {description}: {cmd_str}")

        try:
            # Start the process using Popen
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for the process with timeout
            try:
                stdout, stderr = process.communicate(timeout=timeout)

                # Check if the process was successful
                if process.returncode != 0:
                    error_msg = f"Error executing {description}: {stderr}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                logger.debug(f"{description.capitalize()} output: {stdout}")
                return stdout

            except subprocess.TimeoutExpired:
                # Process timed out - try to get any output so far
                # Kill the process
                process.kill()

                # Capture any output that was generated before the timeout
                stdout, stderr = process.communicate()

                # Print and log the captured output
                print(f"\n--- {description.capitalize()} stdout before timeout ---")
                print(stdout)
                print(f"\n--- {description.capitalize()} stderr before timeout ---")
                print(stderr)

                error_msg = (
                    f"{description.capitalize()} timed out after {timeout} seconds"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg) from None

        except subprocess.CalledProcessError as e:
            error_msg = f"Error executing {description}: {e.stderr}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            if not isinstance(e, RuntimeError):  # Avoid re-wrapping our own exceptions
                error_msg = f"Unexpected error during {description}: {str(e)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            raise
