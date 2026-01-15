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
from openstack import connection
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

    def get_unused_floating_ip(self, first_only: bool = True) -> str | list[str] | None:
        """
        Fetch unused floating IP(s) from OpenStack using application credentials
        loaded from environment variables.

        Returns:
            - dict: {"id": <floating_ip_id>, "address": <floating_ip_address>} if first_only=True
            - list[dict]: list of unused IPs if first_only=False
            - None: if no unused IPs are available
        """

        required_env_vars = [
            "TF_VAR_openstack_auth_url",
            "TF_VAR_openstack_application_credential_id",
            "TF_VAR_openstack_application_credential_secret",
        ]

        missing = [v for v in required_env_vars if not os.environ.get(v)]
        if missing:
            raise RuntimeError(
                f"Missing OpenStack environment variables: {', '.join(missing)}"
            )

        logger.info("Connecting to OpenStack to fetch unused floating IPs")

        conn = connection.Connection(
            auth_url=os.environ["TF_VAR_openstack_auth_url"],
            auth_type="v3applicationcredential",
            application_credential_id=os.environ["TF_VAR_openstack_application_credential_id"],
            application_credential_secret=os.environ["TF_VAR_openstack_application_credential_secret"],
        )

        unused_ips = [
            {"id": ip.id, "address": ip.floating_ip_address}
            for ip in conn.network.ips()
            if not ip.port_id
        ]

        if not unused_ips:
            logger.warning("No unused floating IPs found in the project")
            return None

        if first_only:
            logger.info(f"Selected floating IP: {unused_ips[0]['address']}")
            return unused_ips[0]

        logger.info(f"Found {len(unused_ips)} unused floating IPs")
        return unused_ips

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
        if cloud == "openstack" and "floating_ip" not in config:
            logger.info("OpenStack detected and floating_ip not provided, attempting auto-discovery")

            floating_ip_info = self.get_unused_floating_ip(first_only=True)
            if not floating_ip_info:
                raise RuntimeError("No unused floating IPs available in OpenStack for the project")

            # Inject separately
            config["floating_ip"] = floating_ip_info["address"]      # For SSH, outputs, scripts
            config["floating_ip_id"] = floating_ip_info["id"]        # For Terraform association

            logger.info(
                f"Injected floating_ip={config['floating_ip']} and floating_ip_id={config['floating_ip_id']} into configuration"
            )
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
        if prepared_config.get("cloud") == "openstack":
            logger.info("OpenStack deployment detected, checking for unused floating IP")

            floating_ip = self.get_unused_floating_ip(first_only=True)

            if not floating_ip:
                raise RuntimeError(
                    "Deployment aborted: no unused floating IPs available."
                    "Cloud admin must allocate floating IPs to the project."
                )

            config["floating_ip"] = floating_ip["address"]
            config["floating_ip_id"] = floating_ip["id"]         
        
        # Add output blocks for the module you just added
        module_name = prepared_config["resource_name"]
        logger.info(f"---------- Starting deployment of {module_name} ({role}) ----------")
        outputs_file = os.path.join(cluster_dir, "outputs.tf")
        
        # Define common output names
        output_names = ["cluster_name", "master_ip", "worker_ip", "ha_ip", "k3s_token", "resource_name"]
        
        # Include additional outputs based on the cloud type
        if "aws" in cluster_dir:
            output_names.append("instance_status")
        elif "openstack" in cluster_dir:
            output_names.append("instance_power_state")

        # Add output blocks
        hcl.add_output_blocks(outputs_file, module_name, output_names)

        logger.info(f"Adding node to cluster '{prepared_config['cluster_name']}'")

        # Deploy the infrastructure
        try:
            self.deploy(cluster_dir, module_name, dryrun)
            cluster_name = prepared_config["cluster_name"]
            resource_name = prepared_config["resource_name"]
            logger.info(
                f"✅ Successfully added '{resource_name}' for cluster '{cluster_name}'"
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
                "resource_name": outputs.get("resource_name", {}).get("value")
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
        self, cluster_name: str, resource_name: str, dryrun: bool = False
    ) -> None:
        """
        Remove a specific node except edge from a cluster.

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
        
        env_vars = os.environ.copy()

        # Path to main.tf
        main_tf_path = os.path.join(cluster_dir, "main.tf")

        if not os.path.exists(main_tf_path):
            error_msg = f"Main Terraform file not found: {main_tf_path}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            # Select the workspace
            if not dryrun:
                CommandExecutor.run_command(
                    ["tofu", "workspace", "select", resource_name],
                    cwd=cluster_dir,
                    description=f"Selecting workspace '{resource_name}'",
                    env=env_vars,
                )
            else:
                logger.info(f"Dryrun: select workspace '{resource_name}'")
            
            # Destroy the infrastructure
            if not dryrun:
                CommandExecutor.run_command(
                    ["tofu", "destroy", "-auto-approve"],
                    cwd=cluster_dir,
                    description=f"Destroying infrastructure for '{resource_name}'",
                    env=env_vars,
                )
            else:
                logger.info(f"Dryrun: would destroy infrastructure for '{resource_name}'")

            # Switch back to default workspace
            if not dryrun:
                CommandExecutor.run_command(
                    ["tofu", "workspace", "select", "default"],
                    cwd=cluster_dir,
                    description="Switching back to default workspace",
                    env=env_vars,
                )
            else:
                logger.info("Dryrun: would switch back to default workspace")

            # Remove module block from main.tf
            hcl.remove_module_block(main_tf_path, resource_name)
            logger.info(f"Removed module block for '{resource_name}'")

            # Delete outputs.tf entirely (optional, safer for decentralized setup)
            outputs_tf_path = os.path.join(cluster_dir, "outputs.tf")
            if os.path.exists(outputs_tf_path):
                os.remove(outputs_tf_path)
                logger.debug(f"Deleted outputs.tf to ensure stale outputs do not affect 'tofu apply' for '{resource_name}'")

            # Apply OpenTofu configuration to update state
            if not dryrun:
                CommandExecutor.run_command(
                    ["tofu", "apply", "-auto-approve"],
                    cwd=cluster_dir,
                    description=f"Applying OpenTofu configuration after removing node {resource_name}", env=env_vars
                )
            else:
                logger.info(f"Dryrun: would apply OpenTofu configuration after removing node '{resource_name}'")

            # Delete the workspace
            if not dryrun:
                CommandExecutor.run_command(
                    ["tofu", "workspace", "delete", "-force", resource_name],
                    cwd=cluster_dir,
                    description=f"Deleting workspace '{resource_name}'",
                    env=env_vars,
                )
            else:
                logger.info(f"Dryrun: would delete workspace '{resource_name}'")

            logger.info(f"----------- Removal of node '{resource_name}' from cluster '{cluster_name}' complete -----------")

        except RuntimeError  as e:
            error_msg = f"❌ Failed to remove node '{resource_name}' from cluster '{cluster_name}': {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def deploy(self, cluster_dir: str,workspace: str = "default", dryrun: bool = False) -> None:
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
            
            # Create/select workspace
            try:
                result = subprocess.run(
                    ["tofu", "workspace", "list"],
                    cwd=cluster_dir,
                    capture_output=True,
                    text=True,
                    check=True,
                    env=env_vars,
                )
                existing_workspaces = [line.strip("* ").strip() for line in result.stdout.splitlines()]
            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Failed to list workspaces: {e.stderr or str(e)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            if workspace not in existing_workspaces:
                try:
                    CommandExecutor.run_command(
                        ["tofu", "workspace", "new", workspace],
                        cluster_dir,
                        f"OpenTofu workspace new {workspace}",
                        env=env_vars,
                    )
                except RuntimeError as e:
                    error_msg = f"❌ Failed to create workspace '{workspace}': {str(e)}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

            # Select workspace
            try:
                CommandExecutor.run_command(
                    ["tofu", "workspace", "select", workspace],
                    cluster_dir,
                    f"OpenTofu workspace select {workspace}",
                    env=env_vars,
                )
            except RuntimeError as e:
                error_msg = f"❌ Failed to select workspace '{workspace}': {str(e)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

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
                ["tofu", "apply", "-auto-approve", f"-target=module.{workspace}"], cluster_dir, f"OpenTofu apply for {workspace}", env=env_vars
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
            dryrun: If True, only deletes local cluster directory without touching infra

        Raises:
            RuntimeError: If destruction fails
        """
        logger.info(f"---------- Destroying the cluster '{cluster_name}' -----------")

        # Get the cluster directory
        cluster_dir = self.get_cluster_output_dir(cluster_name)

        # Fail early if the cluster directory does not exist
        if not os.path.exists(cluster_dir):
            error_msg = f"❌ Cluster directory '{cluster_dir}' not found. Cannot safely destroy."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Dry-run mode
        if dryrun:
            logger.info("Dryrun: only removing local cluster directory")
            shutil.rmtree(cluster_dir, ignore_errors=True)
            return

        # Ensure backend exists
        backend_tf_path = os.path.join(cluster_dir, "backend.tf")

        conn_str = self.pg_config.get_connection_string()
        hcl.add_backend_config(backend_tf_path, conn_str, schema_name=cluster_name)

        env_vars = os.environ.copy()
        env_vars["TF_IN_AUTOMATION"] = "true"

        # Initialize OpenTofu
        try:
            CommandExecutor.run_command(
                ["tofu", "init", "-reconfigure"],
                cluster_dir, "initializing backend", env=env_vars
            )
            logger.debug(" Backend initialized successfully.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"❌ Backend init failed: {e.stderr or e}")

        # List all workspaces
        try:
            result = CommandExecutor.run_command(
                ["tofu", "workspace", "list"],
                cluster_dir, "listing workspaces", env=env_vars
            )
            workspaces = [line.strip("* ").strip() 
                          for line in result.splitlines() 
                          if line.strip()]
            logger.debug(f"📋 Found workspaces for cluster '{cluster_name}': {workspaces}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"❌ Failed to list workspaces: {e.stderr or e}")

        # Destroy all non-default workspaces
        for ws in workspaces:
            if ws.lower() == "default":
                continue

            logger.debug(f" Destroying workspace: {ws}")
            try:

                CommandExecutor.run_command(
                    ["tofu", "workspace", "select", ws],
                    cluster_dir,
                    f"select workspace for node {ws}",
                    env=env_vars,
                )

                CommandExecutor.run_command(
                    ["tofu", "destroy", "-auto-approve"],
                    cluster_dir,
                    f"OpenTofu destroy for {ws}",
                    env=env_vars,
                )

                logger.info(f"✅ Successfully destroyed node '{ws}'")

                CommandExecutor.run_command(["tofu", "workspace", "select", "default"],
                            cluster_dir, "switching back to default", env=env_vars)
                CommandExecutor.run_command(["tofu", "workspace", "delete", "-force", ws],
                            cluster_dir, f"deleting workspace {ws}", env=env_vars)
            except RuntimeError as e:
                logger.warning(f"⚠️ Failed to destroy workspace '{ws}': {e.stderr or e}")

        # Drop schema from db and Cleanup local directory
        self.remove_cluster_schema_from_db(cluster_name)
        shutil.rmtree(cluster_dir, ignore_errors=True)
        logger.info(f"🧹 Removed local cluster directory '{cluster_dir}'")

        logger.info(f"----------- Destruction of cluster '{cluster_name}' complete -----------")

    def remove_cluster_schema_from_db(self, cluster_name: str) -> None:
            """
            Removes the schema and the entry for the cluster from the PostgreSQL database.

            Args:
                cluster_name: The name of the cluster to remove from the database

            Raises:
                RuntimeError: If the database operation fails
            """
            logger.debug(f"Removing schema for cluster '{cluster_name}' from the PostgreSQL database...")

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

                logger.info(f"🧹 Dropped schema for cluster '{cluster_name}' from the database")

            except psycopg2.Error as e:
                logger.error(f"❌ Failed to remove schema for cluster '{cluster_name}' from the database: {e}")
                raise RuntimeError(f" ❌Failed to remove schema for cluster '{cluster_name}' from the database")

            finally:
                # Close the database connection
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()

    def deploy_manifests(
        self,
        manifest_folder: str,
        master_ip: str,
        ssh_key_path: str,
        ssh_user: str,
    ):
        """
        Copy and apply manifests to a cluster using copy_manifest.tf in a temporaryfolder.

        Args:
            manifest_folder: Path to local manifest folder
            master_ip: IP address of K3s master
            ssh_key_path: Path to SSH private key
            ssh_user: SSH username to connect to the master node
        """
        # Dedicated folder for copy-manifest operations
        copy_dir = Path(self.output_dir) / "copy-manifest"
        copy_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Using copy-manifest folder: {copy_dir}")

        try:
            # Copy copy_manifest.tf from templates
            tf_source_file = Path(self.template_manager.templates_dir) / "deploy_manifest.tf"
            if not tf_source_file.exists():
                logger.debug(f"deploy_manifest.tf not found at: {tf_source_file}")
                raise RuntimeError(f"deploy_manifest.tf not found at: {tf_source_file}")
            shutil.copy(tf_source_file, copy_dir)
            logger.debug(f"Copied copy_manifest.tf to {copy_dir}")

            # Prepare environment for OpenTofu
            env_vars = os.environ.copy()
            env_vars["TF_LOG"] = os.getenv("TF_LOG", "INFO")
            env_vars["TF_LOG_PATH"] = os.getenv("TF_LOG_PATH", "/tmp/opentofu.log")

            logger.info(f"------------ Applying manifest on node: {master_ip} -------------------")

            # Run tofu init with spinner
            CommandExecutor.run_command(
                ["tofu", "init"],
                cwd=str(copy_dir),
                description="OpenTofu init",
                env=env_vars,
            )

            # Run tofu apply with spinner
            CommandExecutor.run_command(
                [
                    "tofu",
                    "apply",
                    "-auto-approve",
                    f"-var=manifest_folder={manifest_folder}",
                    f"-var=master_ip={master_ip}",
                    f"-var=ssh_private_key_path={ssh_key_path}",
                    f"-var=ssh_user={ssh_user}"
                ],
                cwd=str(copy_dir),
                description="OpenTofu apply",
                env=env_vars,
            )

            logger.info("------------ Successfully applied manifests -------------------")

        except RuntimeError as e:
            print(f"\n---------- ERROR ----------\n{e}\n")
            raise

        finally:
            if copy_dir.exists():
                shutil.rmtree(copy_dir)

    def create_registry_secrets(self, cluster_config: dict):
        """
        Create Docker registry secrets in Kubernetes using OpenTofu.

        :param cluster_config: dict with keys:
            {
                "master_ip": "1.2.3.4",
                "ssh_user": "ubuntu",
                "ssh_private_key_path": "/path/to/key.pem",
                "namespace": "optional-namespace",
                "secret_names": ["optional-name1", "optional-name2"]
            }
        """
        load_dotenv()

        # Read registry creds from env
        registries = os.getenv("DOCKER_REGISTRIES", "").split(",")
        usernames = os.getenv("DOCKER_USERNAMES", "").split(",")
        passwords = os.getenv("DOCKER_PASSWORDS", "").split(",")

        if not (len(registries) == len(usernames) == len(passwords)):
            raise RuntimeError("Mismatch in registry, username, and password counts")

        # Get cluster connection from method input
        master_ip = cluster_config.get("master_ip")
        ssh_user = cluster_config.get("ssh_user")
        ssh_key_path = cluster_config.get("ssh_private_key_path")
        namespace = cluster_config.get("namespace", "default")
        secret_names = cluster_config.get("secret_names", [])

        if not all([master_ip, ssh_user, ssh_key_path]):
            raise ValueError("Cluster config missing required keys")

        # Validate secret_names length if provided
        if secret_names and len(secret_names) != len(registries):
            raise RuntimeError("Length of secret_names must match number of registries")

        # Create temp dir for TF
        temp_dir = Path(self.output_dir) / "registry-secret"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy template tf file into temp dir
            tf_source_file = Path(self.template_manager.templates_dir) / "registry_secret.tf"
            if not tf_source_file.exists():
                logger.debug(f"registry_secret.tf not found at: {tf_source_file}")
                raise RuntimeError(f"registry_secret.tf not found at: {tf_source_file}")

            tf_target = temp_dir / "registry_secret.tf"
            shutil.copy(tf_source_file, tf_target)
            logger.debug(f"Copied registry_secret.tf to {temp_dir}")

            # Setup env for tofu
            env_vars = os.environ.copy()
            env_vars["TF_LOG"] = os.getenv("TF_LOG", "INFO")

            # tofu init
            CommandExecutor.run_command(
                ["tofu", "init"],
                cwd=str(temp_dir),
                description="Init OpenTofu",
                env=env_vars,
            )

            # Apply registry secrets
            apply_vars = [
                f"-var=registries={json.dumps(registries)}",
                f"-var=usernames={json.dumps(usernames)}",
                f"-var=passwords={json.dumps(passwords)}",
                f"-var=master_ip={master_ip}",
                f"-var=ssh_user={ssh_user}",
                f"-var=ssh_private_key_path={ssh_key_path}",
                f"-var=namespace={namespace}"
            ]
            if secret_names:
                apply_vars.append(f"-var=secret_names={json.dumps(secret_names)}")

            CommandExecutor.run_command(
                ["tofu", "apply", "-auto-approve"] + apply_vars,
                cwd=str(temp_dir),
                description="Apply registry secrets",
                env=env_vars,
            )

            # Fetch Terraform/OpenTofu output
            output_result = CommandExecutor.run_command(
                ["tofu", "output", "-json", "docker_registry_secret_names"],
                cwd=str(temp_dir),
                description="Fetch registry secret names",
                env=env_vars,
            )

            lines = [line for line in output_result.splitlines() if line.strip()]
            if not lines:
                raise RuntimeError("No output received from OpenTofu for secret names")
            secret_names_list = json.loads(lines[-1])
            logger.info(f"Created registry secrets: {secret_names_list}")

            return secret_names_list

        finally:
            logger.debug(f"Cleaning up temp dir: {temp_dir}")
            shutil.rmtree(temp_dir)