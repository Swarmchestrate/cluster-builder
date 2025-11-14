"""
Command execution utilities for infrastructure management.
"""

import subprocess
import logging

from yaspin import yaspin
from yaspin.spinners import Spinners

logger = logging.getLogger("swarmchestrate")


class CommandExecutor:
    """Utility for executing shell commands with proper logging and error handling."""

    @staticmethod
    def run_command(
        command: list,
        cwd: str,
        description: str = "command",
        timeout: int = None,
        env: dict = None,  # <-- Add optional env param
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
        logger.debug(f"Running {description}: {cmd_str}")

        show_spinner = timeout is None or timeout > 5

        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        if show_spinner:
            try:
                process.wait(timeout=5)
                stdout, stderr = process.communicate()
                return CommandExecutor._check_result(stdout, stderr, process.returncode, description)
            except subprocess.TimeoutExpired:
                pass  # Still running → spinner starts

        # Either timeout <= 5s, or process still running after 5s
        spinner = yaspin(Spinners.point, text=f"Running {description}...", color="cyan") if show_spinner else None
        if spinner:
            spinner.start()

        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            if spinner:
                spinner.fail("⏰")
            raise RuntimeError(f"{description.capitalize()} timed out after {timeout} seconds")

        if spinner:
            spinner.ok("✅") if process.returncode == 0 else spinner.fail("💥")

        return CommandExecutor._check_result(stdout, stderr, process.returncode, description)

    @staticmethod
    def _check_result(stdout, stderr, returncode, description):
        if returncode != 0:
            err = f"Error executing {description}: {stderr}"
            logger.error(err)
            raise RuntimeError(err)
        logger.debug(f"{description.capitalize()} output: {stdout}")
        return stdout
