# Swarmchestrate - Cluster Builder

This repository contains the codebase for **[cluster-builder]**, which builds K3s clusters for Swarmchestrate using OpenTofu.  

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
4. **OpenTofu**: Version 1.6 or higher for infrastructure provisioning.
6. **Make**: To run the provided `Makefile`.
7. **PostgreSQL**: For storing OpenTofu state.
8. (Optional) **Docker**: To create a dev Postgres
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

**Optional**

```bash
 make db
```

This command will:
- Spin up an empty dev Postgres DB (in Docker) for storing state

### 4. Populate .env file with access config

First, rename or copy the example file to `.env`

```bash
cp .env_example .env
```

Then populate postgres connection details and needed cloud credential data.

```
## PG Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_HOST=db.example.com
POSTGRES_DATABASE=terraform_state
POSTGRES_SSLMODE=prefer

## AWS Auth
AWS_REGION=us-west-2
AWS_ACCESS_KEY=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

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

### Creating a New Cluster

To create a new k3s cluster, use the `add_node` method with the `master` role:

```python
# Configuration for a new cluster
config = {
    "cloud": "aws",
    "k3s_role": "master",
    "ami": "ami-0123456789abcdef",
    "instance_type": "t3.medium",
    "ssh_key_name": "your-ssh-key",
    "k3s_token": "your-k3s-token"
}

# Create the cluster (returns the cluster name)
cluster_name = orchestrator.add_node(config)
print(f"Created cluster: {cluster_name}")
```

### Adding Nodes to an Existing Cluster

To add worker or high-availability nodes to an existing cluster:

```python
# Configuration for adding a worker node
worker_config = {
    "cloud": "aws",
    "k3s_role": "worker",  # can be "worker" or "ha"
    "master_ip": "1.2.3.4",  # IP of the master node
    "cluster_name": "existing-cluster-name",  # specify an existing cluster
    "ami": "ami-0123456789abcdef",
    "instance_type": "t2.medium",
    "ssh_key_name": "your-ssh-key",
    "k3s_token": "k3s-cluster-token" # Token of existing cluster
}

# Add the worker node
cluster_name = orchestrator.add_node(worker_config)
print(f"Added worker node to cluster: {cluster_name}")
```

Important requirements:
- For `k3s_role="worker"` or `k3s_role="ha"`, you must specify a `master_ip`
- For `k3s_role="master"`, you must not specify a `master_ip`

### Removing a Specific Node

To remove a specific node from a cluster:

```python
# Remove a node by its resource name
orchestrator.remove_node(
    cluster_name="your-cluster-name",
    resource_name="aws_eloquent_feynman"  # The resource identifier of the node
)
```

The `remove_node` method:
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

The `destroy` method:
1. Destroys all infrastructure resources associated with the cluster
2. Removes the cluster directory and configuration files

## Advanced Usage

### Dry Run Mode

All operations support a `dryrun` parameter, which validates the configuration 
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
    "cloud": "aws",
    "k3s_role": "master",
    "cluster_name": "production-cluster",
    # ... other configuration ...
}

orchestrator.add_node(config)
```

---

## Template Structure

Templates should be organised as follows:
- `templates/` - Base directory for templates
- `templates/{cloud}/` - Terraform modules for each cloud provider
- `templates/{role}_user_data.sh.tpl` - Node initialisation scripts
- `templates/{cloud}_provider.tf.j2` - Provider configuration templates

---

## Edge Device Requirements

To connect **edge devices** as part of your K3s cluster, ensure that the following **ports are open** on each edge device to enable communication within nodes:

### Inbound Rules:

| Port Range| Protocol| Purpose                                                     |
|-----------|---------|-------------------------------------------------------------|
| 2379-2380 | TCP     | Internal servers communication for embedded etcd            |
| 6443      | TCP     | K3s API server communication                                |
| 8472      | UDP     | Flannel VXLAN (network overlay)                             |
| 10250     | TCP     | Kubelet metrics and communication                           |
| 51820     | UDP     | WireGuard IPv4 (for encrypted networking)                   |
| 51821     | UDP     | WireGuard IPv6 (for encrypted networking)                   |
| 5001      | TCP     | Embedded registry (Spegel)                                  |
| 22        | TCP     | SSH access for provisioning and management                  |
| 80        | TCP     | HTTP communication for web access                           |
| 443       | TCP     | HTTPS communication for secure access                       |
| 53        | UDP     | DNS (CoreDNS) for internal service discovery                |
| 5432      | TCP     | PostgreSQL database access                                  |

### Outbound Rule:

| Port Range| Protocol | Purpose                                                |
|-----------|----------|--------------------------------------------------------|
| all       | all      | Allow all outbound traffic for the system's operations |
