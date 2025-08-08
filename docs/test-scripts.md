# Test Scripts Documentation

This section describes how to run and configure the test scripts used to deploy and manage nodes and clusters in different cloud environments (AWS, OpenStack, and Edge devices) using the `cluster-builder` module.

## Prerequisites

Before running the test scripts, ensure the following:

 **.env File**: Ensure that the `.env` file is provided with correct information. You can find details on how to set this up in the [README](../README.md).

---
## Test Scripts Overview

### 1. test_deploy.py

The test_deploy.py script provisions nodes based on a configuration file. It expects a config.py file with cloud-specific configurations for AWS, OpenStack, and Edge devices.

#### How to Use:
Rename config.py.sample to config.py or create a new config.py with the following format:

```python
# AWS config example
aws_config = {
    "cloud": "aws",
    "k3s_role": "master",
    "k3s_token": "testtoken",
    "ha": False,
    "instance_type": "t2.small",
    "ssh_key_name": "test",
    "ami": "ami-0c0493bbac867d427",
    "ssh_user": "your_user",
    "ssh_private_key_path": "/path/to/key.pem",
}

# OpenStack config example
openstack_config = {
    "cloud": "openstack",
    "openstack_image_id": "6f44fc9-49ad-40e7-a4c1-f313fe413ac9",
    "openstack_flavor_id": "m2.small",
    "ssh_key_name": "test",
    "volume_size": "10",
    "k3s_token": "testtoken",
    "k3s_role": "master",
    "ha": False,
    "ssh_user": "your_user",
    "ssh_private_key_path": "/path/to/key.pem",
}

# Edge device config example
edge_config = {
    "cloud": "edge",
    "edge_device_ip": "10.0.0.1",
    "ssh_user": "your_user",
    "ssh_auth_method": "key",  # "password" or "key"
    "ssh_private_key": "/path/to/key.pem",  # required if ssh_auth_method == "key"
    "k3s_token": "testtoken",
    "k3s_role": "worker",
    "ha": False,
}
```

To run for AWS node: Update the script as follows:

```python
from .config import aws_config  # Use the configuration from config.py
```

To run the script: 

```python
python test_deploy.py
```
---

### 2. test_deploy_json.py
This script allows you to define the configuration for multiple nodes in a JSON file (node_config.json).

#### How to Use:
Rename node_config.json.sample to node_config.json or create a new node_config.json with the following format:

node_config.json Example:
```python
{
  "nodes": [
    {
      "cloud": "aws",
      "k3s_role": "master",
      "k3s_token": "testtoken",
      "ha": false,
      "instance_type": "t2.small",
      "ssh_key_name": "g",
      "ssh_user": "ec2-user",
      "ssh_private_key_path": "/workspaces/cluster-builder/scripts/g.pem",
      "ami": "ami-0c0493bbac867d427",
      "tcp_ports": [10020],
      "udp_ports": [1003]
    },
    {
      "cloud": "openstack",
      "openstack_image_id": "b2be6f4e-ebd8-42af-a526-63691a4d90ea",
      "openstack_flavor_id": "m2.small",
      "ssh_key_name": "micado",
      "volume_size": "10",
      "k3s_token": "testtoken",
      "k3s_role": "master",
      "ha": false,
      "ssh_user": "ubuntu",
      "ssh_private_key_path": "/workspaces/cluster-builder/scripts/micado.pem",
      "floating_ip_pool": "ext-net",
      "network_id":"bbe042e4-91a1-4601-962f-14a31e5e2787",
      "use_block_device":true,
      "tcp_ports": [31200],
      "udp_ports": [4011]
    }
  ]
}
```

To run the script: 

```python
python test_deploy_json.py
```
---

### 3. test_deploy_cluster_json.py
This script expects a cluster_config.json file for defining clusters with multiple nodes.

#### How to Use:
Rename cluster_config.json.sample to cluster_config.json or create a new cluster_config.json with the following format:

cluster_config.json Example:

```json
{
  "k3s_token": "sampletoken1234567890",
  "nodes": [
    {
      "cloud": "aws",
      "k3s_role": "master",
      "ha": false,
      "instance_type": "t2.small",
      "ssh_key_name": "test",
      "ssh_user": "ec2-user",
      "ssh_private_key_path": "/path/to/key.pem",
      "ami": "ami-0c0493bbac867d427",
      "security_group_id": "sg-0123456789abcdef0",
      "tcp_ports": [10020],
      "udp_ports": [1003]
    },
    {
      "cloud": "openstack",
      "openstack_image_id": "b2be6f4e-ebd8-42af-a526-63691a4d90ea",
      "openstack_flavor_id": "m2.small",
      "ssh_key_name": "test",
      "volume_size": "10",
      "k3s_role": "worker",
      "ha": false,
      "ssh_user": "ubuntu",
      "ssh_private_key_path": "/path/to/key.pem",
      "floating_ip_pool": "ext-net",
      "network_id": "bbe042e4-91a1-4601-962f-14a31e5e2787",
      "use_block_device": true,
      "security_group_id": "f05b97f0-140a-4d24-bfc6-3a197e842739",
      "tcp_ports": [10020],
      "udp_ports": [1003]
    }
  ]
}
```

Run the script: This script will deploy the cluster as defined in cluster_config.json.
To run the script: 

```python
python test_deploy_cluster_json.py
```
---

### 4. test_remove.py
This script removes a specific node from a cluster.

#### How to Use: Update the CLUSTER_NAME and NODE_NAME variables in the script:

```python
CLUSTER_NAME = "boring_liskov"
NODE_NAME = "aws_sweet_swanson"
```
Run the script to remove the node from the cluster.

To run the script: 

```python
python test_remove.py
```

---

### 5. test_destroy.py
This script destroys an entire cluster, removing all associated nodes and infrastructure.

#### How to Use: Update the CLUSTER_NAME variable:

```python
CLUSTER_NAME = "quizzical_shamir"
```
Run the script to destroy the cluster. Note: For edge devices, the script will not remove the K3s installation, and you will need to manually uninstall K3s from the edge device.

To run the script: 

```python
python test_destroy.py
```
---