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
5. **PostgreSQL**: For storing OpenTofu state.
6. (Optional) **Docker**: To create a dev Postgres
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

#### 4.2. Open the **.env** file and add the necessary configuration for your cloud providers and PostgreSQL:

```ini
## PG Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_HOST=db.example.com
POSTGRES_DATABASE=terraform_state
POSTGRES_SSLMODE=prefer

## AWS Auth
TF_VAR_aws_region=us-west-2
TF_VAR_aws_access_key=AKIAXXXXXXXXXXXXXXXX
TF_VAR_aws_secret_key=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

## OpenStack Auth - AppCreds Mode
TF_VAR_openstack_auth_method=appcreds
TF_VAR_openstack_auth_url=https://openstack.example.com:5000
TF_VAR_openstack_application_credential_id=fdXXXXXXXXXXXXXXXX
TF_VAR_openstack_application_credential_secret=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TF_VAR_openstack_region=RegionOne

## OpenStack Auth - User/Pass Mode
# TF_VAR_openstack_auth_method=userpass
# TF_VAR_openstack_auth_url=https://openstack.example.com:5000
# TF_VAR_openstack_region=RegionOne
# TF_VAR_openstack_user_name=myuser
# TF_VAR_openstack_password=mypassword
# TF_VAR_openstack_project_id=project-id-123
# TF_VAR_openstack_user_domain_name=Default
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

To create a new k3s cluster, use the **add_node** method with the **master** role:

```python
# Configuration for a new cluster using aws provider
config = {
    "cloud": "aws", 
    "k3s_role": "master", 
    "ha": False,  # Set to True for high availability (HA) deployments
    "instance_type": "t2.small",  # AWS instance type
    "ssh_key_name": "g",  # SSH key name for AWS or OpenStack
    "ssh_user": "ec2-user",  # SSH user for the instance
    "ssh_private_key_path": "/workspaces/cluster-builder/scripts/g.pem",  # Path to SSH private key
    "ami": "ami-0c0493bbac867d427",  # AMI ID for AWS (specific to region)
    # Optional parameters
    # If existing SG is specified, it will be used directly with no port changes
    "security_group_id": "sg-0123456789abcdef0",
    # No security_group_id means a new SG will be created and these ports applied as rules
    # These ports will be used ONLY if creating a new SG
    "tcp_ports": [10020],  # Optional list of TCP ports to open
    "udp_ports": [1003]  # Optional list of UDP ports to open
}

# Create the cluster (returns the cluster name)
cluster_name = orchestrator.add_node(config)
print(f"Created cluster: {cluster_name}")
```

Note: Fetch the outputs from the master node and use them when adding a worker node.

### Adding Nodes to an Existing Cluster

To add worker or high-availability nodes to an existing cluster:

```python
# Configuration for adding a worker node using aws provider
worker_config = {
    "cloud": "aws",
    "k3s_role": "worker",  # Role can be 'worker' or 'ha'
    "instance_type": "t2.small",  # AWS instance type
    "ssh_key_name": "g",  # SSH key name
    "ssh_user": "ec2-user",  # SSH user for the instance
    "ssh_private_key_path": "/workspaces/cluster-builder/scripts/g.pem",  # Path to SSH private key
    "ami": "ami-0c0493bbac867d427",  # AMI ID for AWS
    # Additional parameters obtained after deploying the master node:
    "master_ip": "12.13.14.15",  # IP address of the master node (required for worker/HA roles)
    "cluster_name": "elastic_mcnulty",  # Name of the cluster
    "k3s_token": "G4lm7wEaFuCCygeU", # Token of the cluster
    # Optional parameters
    # If existing SG is specified, it will be used directly with no port changes
    "security_group_id": "sg-0123456789abcdef0",
    # No security_group_id means a new SG will be created and these ports applied as rules
    # These ports will be used ONLY if creating a new SG
    "tcp_ports": [10020],  # Optional list of TCP ports to open
    "udp_ports": [1003]  # Optional list of UDP ports to open
}

# Add the worker node
cluster_name = orchestrator.add_node(worker_config)
print(f"Added worker node to cluster: {cluster_name}")
```

### Removing a Specific Node

To remove a specific node from a cluster:

```python
# Remove a node by its resource name
orchestrator.remove_node(
    cluster_name="your-cluster-name",
    resource_name="aws_eloquent_feynman"  # The resource identifier of the node
)
```

The **remove_node** method:
1. Destroys the node's infrastructure resources
2. Removes the node's configuration from the cluster

---

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

---
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

## Important Configuration Requirements
### High Availability Flag (ha):

- The ha flag should be set to True for high availability deployment (usually when adding a ha or worker node to an existing master).

### SSH Credentials:

- For all roles (k3s_role="master", k3s_role="worker", k3s_role="ha"), you must specify both ssh_user and ssh_private_key_path except for edge.

- The ssh_private_key_path should be the path to your SSH private key file. Ensure that the SSH key is copied to the specified path before running the script.

- The ssh_key_name and the ssh_private_key_path are different—ensure that your SSH key is placed correctly at the provided ssh_private_key_path.

### Ports:
You can specify custom ports for your nodes in the tcp_ports and udp_ports fields. However, certain ports are required for Kubernetes deployment (even if not specified explicitly):

**TCP Ports:**

- 2379-2380: For etcd communication
- 6443: K3s API server
- 10250: Kubelet metrics
- 51820-51821: WireGuard (for encrypted networking)
- 22: SSH access
- 80, 443: HTTP/HTTPS access
- 53: DNS (CoreDNS)
- 5432: PostgreSQL access (master node)

**UDP Ports:**

- 8472: VXLAN for Flannel
- 53: DNS

### OpenStack:
When provisioning on OpenStack, you should provide the value for 'floating_ip_pool' from which floating IPs can be allocated for the instance. If not specified, OpenTofu will not assign floating IP.

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

## DEMO
Some test scripts have been created for demonstrating the functionality of the cluster builder. These scripts can be referred to for understanding how the system works and for testing various configurations.

For detailed service deployment examples and to explore the test scripts, refer to the [test scripts](docs/test-scripts.md) document

---