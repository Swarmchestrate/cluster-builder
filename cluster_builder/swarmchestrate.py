"""
Swarmchestrate - Main orchestration class for K3s cluster management.
"""

import json
import os
import logging
from pathlib import Path
import shutil
import subprocess
from typing import Optional
import psycopg2

from dotenv import load_dotenv

from cluster_builder.config.postgres import PostgresConfig
from cluster_builder.config.cluster import ClusterConfig
from cluster_builder.infrastructure import TemplateManager
from cluster_builder.infrastructure import CommandExecutor
from cluster_builder.utils import hcl

logger = logging.getLogger("swarmchestrate")


class Swarmchestrate:
    """
    Main class for orchestrating K3s clusters across different cloud providers.
    """

    def __init__(
        self,
        template_dir: str,
        output_dir: str,
        variables: Optional[dict[str, any]] = None,
    ):
        """
        Initialise the Swarmchestrate class.

        Args:
            template_dir: Directory containing templates
            output_dir: Directory for outputting generated files
            variables: Optional additional variables for deployments
        """
        self.template_dir = f"{template_dir}"
        self.output_dir = output_dir

        load_dotenv()

        try:
            logger.debug("Loading PostgreSQL configuration from environment...")
            self.pg_config = PostgresConfig.from_env()
        except ValueError as e:
            logger.error(f"Invalid PostgreSQL configuration: {e}")
            raise

        # Initialise components
        self.template_manager = TemplateManager()
        self.cluster_config = ClusterConfig(self.template_manager, output_dir)

        logger.debug(
            f"Initialised with template_dir={template_dir}, output_dir={output_dir}"
        )

    def get_cluster_output_dir(self, cluster_name: str) -> str:
        """
        Get the output directory path for a specific cluster.

        Args:
            cluster_name: Name of the cluster

        Returns:
            Path to the cluster output directory
        """
        return self.cluster_config.get_cluster_output_dir(cluster_name)

    def validate_configuration(self, cloud: str, config: dict) -> list:
        """
        Validate a configuration against the required variables for a cloud provider.

        Args:
            cloud: Cloud provider name
            config: Configuration dictionary provided by the user

        Returns:
            List of missing required variables (empty if all required variables are present)
        """
        logger.debug(f"Validating configuration for cloud={cloud}, role={config.get('k3s_role')}")
        # Master IP validation
        has_master_ip = "master_ip" in config and config["master_ip"]
        role = config["k3s_role"]

        # Cannot add a master node to an existing cluster
        if has_master_ip and role == "master":
            logger.error("Invalid configuration: master_ip specified with master role")
            raise ValueError(
                "Cannot add master to existing cluster (master_ip specified with master role)"
            )

        # Worker/HA nodes require a master IP
        if not has_master_ip and role in ["worker", "ha"]:
            logger.error(f"Invalid configuration: Role '{role}' requires master_ip to be specified")
            raise ValueError(f"Role '{role}' requires master_ip to be specified")

        required_vars = self.template_manager.get_required_variables(cloud)

        # Find missing required variables
        missing_vars = []
        for var_name, var_config in required_vars.items():
            # If variable has no default and is not in config, it's required but missing
            if "default" not in var_config and var_name not in config:
                missing_vars.append(var_name)

        if missing_vars:
            logger.warning(f"⚠️ Missing required variables for {cloud}: {missing_vars}")
        else:
            logger.debug(f"All required variables provided for {cloud}")

        return missing_vars

    def prepare_infrastructure(
        self, config: dict[str, any]
    ) -> tuple[str, dict[str, any]]:
        """
        Prepare infrastructure configuration for deployment.

        This method prepares the necessary files and configuration for deployment
        but does not actually deploy the infrastructure.

        Args:
            config: Configuration dictionary containing cloud, k3s_role, and
                optionally cluster_name and master_ip

        Returns:
            Tuple containing the cluster directory path and updated configuration

        Raises:
            ValueError: If required configuration is missing or invalid
            RuntimeError: If file operations fail
        """
        try:
            logger.debug("Preparing infrastructure configuration...")
            # Prepare the configuration
            cluster_dir, prepared_config = self.cluster_config.prepare(config)
            logger.debug(f"Cluster directory prepared at: {cluster_dir}")
        
            # Validate the configuration
            cloud = prepared_config["cloud"]
            missing_vars = self.validate_configuration(cloud, prepared_config)
            if missing_vars:
                raise ValueError(
                    f"Missing required variables for cloud provider '{cloud}': {', '.join(missing_vars)}"
                )
            logger.debug(f"Configuration validated for cloud: {cloud}")

            # Create provider configuration
            if cloud!= "edge" :
                self.template_manager.create_provider_config(cluster_dir, cloud)
                logger.debug(f"Created provider configuration for {cloud}")
            else:
                logger.debug("Skipping provider configuration for edge.")

            # Create Terraform files
            main_tf_path = os.path.join(cluster_dir, "main.tf")
            backend_tf_path = os.path.join(cluster_dir, "backend.tf")

            # Add backend configuration

            # Add PostgreSQL connection string to config
            conn_str = self.pg_config.get_connection_string()
            hcl.add_backend_config(
                backend_tf_path,
                conn_str,
                prepared_config["cluster_name"],
            )
            logger.debug(f"Added backend configuration to {backend_tf_path}")

            # Add module block
            target = prepared_config["resource_name"]
            hcl.add_module_block(main_tf_path, target, prepared_config)
            logger.debug(f"Added module block to {main_tf_path}")
            logger.debug("Infrastructure preparation complete.")

            return cluster_dir, prepared_config

        except Exception as e:
            error_msg = f"❌ Failed to prepare infrastructure: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def add_node(self, config: dict[str, any], dryrun: bool = False) -> dict:
        """
        Add a node to an existing cluster or create a new cluster based on configuration.

        If master_ip is provided, adds a node to that cluster.
        If master_ip is not provided, creates a new cluster.

        Args:
            config: Configuration dictionary containing cloud, k3s_role, and
                   optionally cluster_name and master_ip
            dryrun: If True, only validate the configuration without deploying

        Returns:
            The cluster name and other output values.

        Raises:
            ValueError: If required configuration is missing or invalid
            RuntimeError: If preparation or deployment fails
        """
        # Prepare the infrastructure configuration
        
        cluster_dir, prepared_config = self.prepare_infrastructure(config)
        role = prepared_config["k3s_role"]
        
        # Add output blocks for the module you just added
        module_name = prepared_config["resource_name"]
        logger.info(f"---------- Starting deployment of {module_name} ({role}) ----------")
        outputs_file = os.path.join(cluster_dir, "outputs.tf")
        
        # Define common output names
        output_names = ["cluster_name", "master_ip", "worker_ip", "ha_ip", "k3s_token", "node_name"]
        
        # Include additional outputs based on the cloud type
        if "aws" in cluster_dir:
            output_names.append("instance_status")
        elif "openstack" in cluster_dir:
            output_names.append("instance_power_state")

        # Add output blocks
        hcl.add_output_blocks(outputs_file, module_name, output_names)

        logger.info(f"Adding node for cluster '{prepared_config['cluster_name']}'")

        # Deploy the infrastructure
        try:
            self.deploy(cluster_dir, dryrun)
            cluster_name = prepared_config["cluster_name"]
            node_name = prepared_config["resource_name"]
            logger.info(
                f"✅ Successfully added '{node_name}' for cluster '{cluster_name}'"
            )
            # Run 'tofu output -json' to get outputs
            result = subprocess.run(
                ["tofu", "output", "-json"],
                cwd=cluster_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            outputs = json.loads(result.stdout)

            # Extract output values for all required fields
            result_outputs = {
                "cluster_name": outputs.get("cluster_name", {}).get("value"),
                "master_ip": outputs.get("master_ip", {}).get("value"),
                "k3s_token": outputs.get("k3s_token", {}).get("value"),
                "worker_ip": outputs.get("worker_ip", {}).get("value"),
                "ha_ip": outputs.get("ha_ip", {}).get("value"),
                "node_name": outputs.get("node_name", {}).get("value")
            }
            # Add cloud-specific output
            if "aws" in cluster_dir:
                result_outputs["instance_status"] = outputs.get("instance_status", {}).get("value")
            elif "openstack" in cluster_dir:
                result_outputs["instance_power_state"] = outputs.get("instance_power_state", {}).get("value")

            logger.info(f"----------- Deployment of {role} node successful -----------")
            logger.debug(f"Deployment outputs: {result_outputs}")

            return result_outputs

        except subprocess.CalledProcessError as e:
            error_msg = f"❌ Failed to get outputs: {e.stderr.strip()}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        except Exception as e:
            error_msg = f"❌ Failed to add node: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)


    def remove_node(
        self, cluster_name: str, resource_name: str, is_edge: bool = False, dryrun: bool = False
    ) -> None:
        """
        Remove a specific node from a cluster.

        This method removes a node's infrastructure component from a cluster by
        removing its module block from the Terraform configuration and then
        reapplying the configuration.

        Args:
            cluster_name: Name of the cluster
            resource_name: Node name in K3s and module name in main.tf / OpenTofu
            is_edge: True if the node is pre-provisioned (edge node)
            dryrun: If True, only simulate actions without executing

        Raises:
            RuntimeError: If node removal fails
        """
        logger.info(f"------------ Removing node '{resource_name}' from cluster '{cluster_name}' ------------")

        # Get the directory for the specified cluster
        cluster_dir = self.get_cluster_output_dir(cluster_name)

        if not os.path.exists(cluster_dir):
            error_msg = f"Cluster directory '{cluster_dir}' not found"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Path to main.tf
        main_tf_path = os.path.join(cluster_dir, "main.tf")

        if not os.path.exists(main_tf_path):
            error_msg = f"Main Terraform file not found: {main_tf_path}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            # Destroy VM only if cloud node (optional)
            if not is_edge:
                tofu_resource = f"opentofu_aws_instance.{resource_name}"
                if not dryrun:
                    CommandExecutor.run_command(
                        ["tofu", "destroy", "-target", tofu_resource, "-auto-approve"],
                        cwd=cluster_dir,
                        description=f"Destroying VM for node {resource_name}",
                    )
                else:
                    logger.info(f"Dryrun: would destroy VM for node '{resource_name}' (cloud node)")

            # Remove module block from main.tf
            hcl.remove_module_block(main_tf_path, resource_name)
            logger.info(f"Removed module block for '{resource_name}' from {main_tf_path}")

            # Delete outputs.tf entirely (optional, safer for decentralized setup)
            outputs_tf_path = os.path.join(cluster_dir, "outputs.tf")
            if os.path.exists(outputs_tf_path):
                os.remove(outputs_tf_path)
                logger.info(f"Deleted outputs.tf before applying changes to remove '{resource_name}'")

            # Apply OpenTofu configuration to update state
            if not dryrun:
                CommandExecutor.run_command(
                    ["tofu", "apply", "-auto-approve"],
                    cwd=cluster_dir,
                    description=f"Applying OpenTofu configuration after removing node {resource_name}",
                )
            else:
                logger.info(f"Dryrun: would apply OpenTofu configuration after removing node '{resource_name}'")

            logger.info(f"✅ Node '{resource_name}' removed successfully from cluster '{cluster_name}'")

        except Exception as e:
            error_msg = f"❌ Failed to remove node '{resource_name}' from cluster '{cluster_name}': {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def deploy(self, cluster_dir: str, dryrun: bool = False) -> None:
        """
        Execute OpenTofu commands to deploy the K3s component with error handling.

        Args:
            cluster_dir: Directory containing the Terraform files for the cluster
            dryrun: If True, only run init and plan without applying

        Raises:
            RuntimeError: If OpenTofu commands fail
        """
        logger.debug(f"Updating infrastructure in {cluster_dir}")

        if not os.path.exists(cluster_dir):
            error_msg = f"❌ Cluster directory '{cluster_dir}' not found"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Retrieve the environment variables for tofu logs
        tf_log = os.getenv("TF_LOG", "INFO")
        tf_log_path = os.getenv("TF_LOG_PATH", "/tmp/opentofu.log")

        # Check if the environment variables are set
        if not tf_log or not tf_log_path:
            print("❌ Error: Missing required environment variables.")
            exit(1)

        # Prepare environment variables for subprocess
        env_vars = os.environ.copy()
        env_vars["TF_LOG"] = tf_log
        env_vars["TF_LOG_PATH"] = tf_log_path

        try:
            # Initialise OpenTofu
            init_command = ["tofu", "init"]
            if dryrun:
                logger.info("Dryrun: will init without backend and validate only")
                init_command.append("-backend=false")
            CommandExecutor.run_command(init_command, cluster_dir, "OpenTofu init", env=env_vars)

            # Validate the deployment
            if dryrun:
                CommandExecutor.run_command(
                    ["tofu", "validate"], cluster_dir, "OpenTofu validate", env=env_vars
                )
                logger.info("✅ Infrastructure successfully validated")
                return

            # Plan the deployment
            CommandExecutor.run_command(
                ["tofu", "plan", "-input=false"],
                cluster_dir,
                "OpenTofu plan",
                timeout=30,
                env=env_vars,
            )

            # Apply the deployment
            CommandExecutor.run_command(
                ["tofu", "apply", "-auto-approve"], cluster_dir, "OpenTofu apply", env=env_vars
            )
            logger.info("Infrastructure successfully updated")

        except RuntimeError as e:
            error_msg = f"❌ Failed to deploy infrastructure: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def destroy(self, cluster_name: str, dryrun: bool = False) -> None:
        """
        Destroy the deployed K3s cluster for the specified cluster_name using OpenTofu.

        Args:
            cluster_name: Name of the cluster to destroy

        Raises:
            RuntimeError: If destruction fails
        """
        logger.info(f"---------- Destroying the cluster '{cluster_name}' -----------")

        # Get the directory for the specified cluster
        cluster_dir = self.get_cluster_output_dir(cluster_name)

        if not os.path.exists(cluster_dir):
            error_msg = f"❌ Cluster directory '{cluster_dir}' not found"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        if dryrun:
            logger.info("Dryrun: will only delete cluster")
            shutil.rmtree(cluster_dir, ignore_errors=True)
            return

        try:

            # Plan destruction
            CommandExecutor.run_command(
                ["tofu", "plan", "-destroy", "-input=false"],
                cluster_dir,
                "OpenTofu plan destruction",
                timeout=40,
            )

            # Execute destruction
            CommandExecutor.run_command(
                ["tofu", "destroy", "-auto-approve"], cluster_dir, "OpenTofu destroy"
            )

            logger.info(f"Cluster '{cluster_name}' destroyed successfully")

            # Remove the cluster directory
            shutil.rmtree(cluster_dir, ignore_errors=True)
            logger.info(f"✅ Removed cluster directory: {cluster_dir}")

            # Remove schema and database entry from PostgreSQL
            self.remove_cluster_schema_from_db(cluster_name)

        except RuntimeError as e:
            error_msg = f"❌ Failed to destroy cluster '{cluster_name}': {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def remove_cluster_schema_from_db(self, cluster_name: str) -> None:
            """
            Removes the schema and the entry for the cluster from the PostgreSQL database.

            Args:
                cluster_name: The name of the cluster to remove from the database

            Raises:
                RuntimeError: If the database operation fails
            """
            logger.info(f"Removing schema for cluster '{cluster_name}' from the PostgreSQL database...")

            # Create a PostgreSQL connection string using the config
            connection_string = self.pg_config.get_connection_string()

            try:
                # Connect to the PostgreSQL database
                connection = psycopg2.connect(connection_string)
                cursor = connection.cursor()

                # Define the SQL query to delete the cluster schema
                drop_schema_query = f'DROP SCHEMA IF EXISTS "{cluster_name}" CASCADE'
                cursor.execute(drop_schema_query)

                # Commit the transaction
                connection.commit()

                logger.info(f"Schema for cluster '{cluster_name}' removed from the database")
                logger.info(f"----------- Destruction of cluster '{cluster_name}' successful -----------")

            except psycopg2.Error as e:
                logger.error(f"❌ Failed to remove schema for cluster '{cluster_name}' from the database: {e}")
                raise RuntimeError(f" ❌Failed to remove schema for cluster '{cluster_name}' from the database")

            finally:
                # Close the database connection
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()

    def run_copy_manifests_tf(
        self,
        manifest_folder: str,
        master_ip: str,
        ssh_key_path: str,
        ssh_user: str,
    ):
        """
        Copy and apply manifests to a cluster using copy_manifest.tf in a separate folder.

        Args:
            manifest_folder: Path to local manifest folder
            master_ip: IP address of K3s master
            ssh_key_path: Path to SSH private key
            ssh_user: SSH username to connect to the master node
        """
        # Dedicated folder for copy-manifest operations
        copy_dir = Path(self.output_dir) / "copy-manifest"
        copy_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using separate copy-manifest folder: {copy_dir}")

        # Copy copy_manifest.tf from templates
        tf_source_file = Path(self.template_manager.templates_dir) / "copy_manifest.tf"
        if not tf_source_file.exists():
            logger.error(f"copy_manifest.tf not found at: {tf_source_file}")
            raise RuntimeError(f"copy_manifest.tf not found at: {tf_source_file}")
        shutil.copy(tf_source_file, copy_dir)
        logger.info(f"Copied copy_manifest.tf to {copy_dir}")

        # Prepare environment for OpenTofu
        env_vars = os.environ.copy()
        env_vars["TF_LOG"] = os.getenv("TF_LOG", "INFO")
        env_vars["TF_LOG_PATH"] = os.getenv("TF_LOG_PATH", "/tmp/opentofu.log")

        try:
            # Initialize OpenTofu in the separate folder
            logger.info(f"Initializing OpenTofu in {copy_dir}...")
            subprocess.run(["tofu", "init"], cwd=copy_dir, check=True, env=env_vars)

            # Apply the copy-manifest resource
            logger.info(f"Applying copy-manifest resource in {copy_dir}...")
            cmd = [
                "tofu",
                "apply",
                "-auto-approve",
                f"-var=manifest_folder={manifest_folder}",
                f"-var=master_ip={master_ip}",
                f"-var=ssh_private_key_path={ssh_key_path}",
                f"-var=ssh_user={ssh_user}"
            ]
            result = subprocess.run(cmd, cwd=copy_dir, check=True, capture_output=True, text=True, env=env_vars)

            # Log output
            if result.stdout:
                logger.info(result.stdout)
            if result.stderr:
                logger.warning(result.stderr)

            logger.info("✅ Copy-manifest applied successfully on master node.")

        except subprocess.CalledProcessError as e:
            error_msg = f"Error applying copy-manifest on master {master_ip}: {e.stderr or e.stdout}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

