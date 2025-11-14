# Swarmchestrate - Cluster Builder

This repository contains the codebase for **cluster-builder**, which builds K3s clusters for Swarmchestrate using OpenTofu.  

Key features:
- **Create**: Provisions infrastructure using OpenTofu and installs K3s.
- **Add**: Add worker or HA nodes to existing clusters.
- **Remove**: Selectively remove nodes from existing clusters.  
- **Delete**: Destroys the provisioned infrastructure when no longer required. 

---

## Prerequisites

Before proceeding, ensure the following prerequisites are installed:

1. **Git**: For cloning the repository.
2. **Python**: Version 3.9 or higher.
3. **pip**: Python package manager.
4. **Make**: To run the provided `Makefile`.
5. **PostgreSQL**: OpenTofu stores its state in a Postgres database.
6. (Optional) **Docker**: Only needed if you want to run the dev Postgres.
7. For detailed instructions on **edge device requirements**, refer to the [Edge Device Requirements](docs/edge-requirements.md) document.

---

## Getting Started

### 1. Clone the Repository

To get started, clone this repository:

```bash
git clone https://github.com/Swarmchestrate/cluster-builder.git
 ```

### 2. Navigate to the Project Directory

```bash
cd cluster-builder
 ```

### 3. Install Dependencies and Tools

Run the Makefile to install all necessary dependencies, including OpenTofu:

```bash
 make install
```

This command will:
- Install Python dependencies listed in requirements.txt.
- Download and configure OpenTofu for infrastructure management.

```bash
 make db
```

This command will:
- Spin up an empty dev Postgres DB (in Docker) for storing state

in ths makefile database details are provide you update or use that ones name pg-db -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=adminpass -e POSTGRES_DB=swarmchestrate

For database setup as a service, refer to the [database setup as service](docs/database_setup.md) document

### 4. Populate .env file with access config
The .env file is used to store environment variables required by the application. It contains configuration details for connecting to your cloud providers, the PostgreSQL database, and any other necessary resources.

#### 4.1.  Rename or copy the example file to **.env**

```bash
cp .env_example .env
```

#### 4.2. Open the **.env** file and add the necessary configuration:
You can see all the available variables in [.env_example](.env_example). Key sections include:
- PostgreSQL connection
- AWS credentials
- OpenStack credentials
- Edge device settings (if applicable)

---

## Basic Usage

### Initialisation

```python
from cluster_builder import Swarmchestrate

# Initialise the orchestrator
orchestrator = Swarmchestrate(
    template_dir="/path/to/templates",
    output_dir="/path/to/output"
)
```

### Adding Nodes (Create a New Cluster or Add to Existing Cluster)

The same add_node method is used both for creating a new cluster (with the master node) and for adding worker or high-availability nodes.

#### 1. 1. Prepare the configuration for your node (AWS, OpenStack, or edge):
You may define it directly as a Python dictionary or load it from a separate file. Refer [config](docs/config-example.md) for details.

#### 2. Load the configuration in Python:

```python
config ={ 
    # your config fields here
}

# Add the node to the cluster (master for new cluster, worker/HA for existing)
cluster_name = orchestrator.add_node(config)
print(f"Created cluster: {cluster_name}")
```

Notes:
- For a new cluster, the first node should be the master. The returned cluster outputs (IP, token) should be used when adding subsequent worker or HA nodes.

- The configuration file defines all required parameters for the node, including cloud provider, K3s role, SSH info, and optional network/security settings.


### Removing a Specific Node

To remove a specific node from a cluster:

```python
# Remove a node by its resource name
orchestrator.remove_node(
    cluster_name="your-cluster-name",
    resource_name="eloquent_feynman"  # The resource identifier of the node
)
```

The **remove_node** method:
1. Destroys the node's infrastructure resources
2. Removes the node's configuration from the cluster

### Destroying an Entire Cluster

To completely destroy a cluster and all its nodes:

```python
# Destroy the entire cluster
orchestrator.destroy(
    cluster_name="your-cluster-name"
)
```

The **destroy** method:
1. Destroys all infrastructure resources associated with the cluster
2. Removes the cluster directory and configuration files

Note for **Edge Devices**:
Since the edge device is already provisioned, the `destroy` method will not remove K3s directly from the edge device. You will need to manually uninstall K3s from your edge device after the cluster is destroyed.

### Deploying Manifests

The deploy_manifests method copies Kubernetes manifests to the target cluster node.

```python
orchestrator.deploy_manifests(
    manifest_folder="path/to/manifests",
    master_ip="MASTER_NODE_IP",
    ssh_key_path="path/to/key.pem",
    ssh_user="USERNAME"
)
```
---

## DEMO
A set of demo scripts is provided to showcase how to deploy a full multi-cloud K3s cluster (AWS master, OpenStack worker, Edge worker), manage manifests, configure registries, remove nodes, and destroy the cluster.

These scripts walk through the entire lifecycle of a cluster and are the recommended starting point for understanding how the system works end-to-end.

For detailed information on how each demo script works, refer [demo scripts](docs/demo-scripts.md) documentation

---

## Important Configuration Requirements
### High Availability Flag (ha):

Set "ha": true when adding an additional server node to an existing master.
Do not set it to true for standalone masters or worker nodes.

### Ports:
You can define additional ports via:

```python
"custom_ingress_ports": [...],
"custom_egress_ports": [...]
```
When a new security group is created, all required K3s and system ports are automatically added, even if you don’t specify them.
Your custom rules are added on top of these defaults.
Only define ports when you need extra application access.

### OpenStack Floating IP:
When provisioning on sztaki openStack, you should provide the value for 'floating_ip_pool' from which floating IPs can be allocated for the instance. If not specified, OpenTofu will not assign floating IP.

---

## Advanced Usage

### Dry Run Mode

All operations support a **dryrun** parameter, which validates the configuration 
without making changes. A node created with dryrun should be removed with dryrun.

```python
# Validate configuration without deploying
orchestrator.add_node(config, dryrun=True)

# Validate removal without destroying
orchestrator.remove_node(cluster_name, resource_name, dryrun=True)

# Validate destruction without destroying
orchestrator.destroy(cluster_name, dryrun=True)
```

### Custom Cluster Names

By default, cluster names are generated automatically. To specify a custom name:

```python
config = {
    "cluster_name": "production-cluster",
    # ... other configuration ...
}
```
---

## Template Structure

Templates should be organised as follows:
- `templates/` - Base directory for templates
- `templates/{cloud}/` - Terraform modules for each cloud provider
- `templates/{role}_user_data.sh.tpl` - Node initialisation scripts
- `templates/{cloud}_provider.tf` - Provider configuration templates

---
## Contact
For any questions or feedback, feel free to reach out:

- Email: G.Kotak@westminster.ac.uk
- Email: J.Deslauriers@westminster.ac.uk

---
