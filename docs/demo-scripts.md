# Demo Scripts Documentation

This section describes the demo scripts prepared for testing and demonstrating the functionality of the cluster-builder module. The scripts help deploy a K3s cluster across AWS, OpenStack, and Edge devices.


## Prerequisites

Before running the test scripts, ensure the following:

 **.env File**: Ensure that the `.env` file is provided with correct information. You can find details on how to set this up in the [README](../README.md).

 **Python dependencies installed**(cluster-builder module and required packages).

---
## Demo Workflow Overview
The demo assumes AWS as the master/server node and OpenStack + Edge devices as worker/agent nodes. The workflow involves sequential deployment:

- Deploy AWS K3s master node.
- Deploy OpenStack worker node(s) using the master node details.
- Deploy Edge worker node(s) using the master node details.

### 1. deploy_k3s_master_aws.py

Deploys the K3s master node on AWS.

#### How to Use:
**Input:** k3s_server_aws.json

Rename k3s_server_aws.json.sample to k3s_server_aws.json or create a new file.

**Output:** A JSON file containing details of the deployed master node

To run the script: 

```python
python deploy_k3s_master_aws.py
```
---

### 2. deploy_k3s_worker_openstack.py
Deploys OpenStack worker node(s) using the AWS master details as input.

#### How to Use:
**Input:** k3s_worker_openstack.json + output from AWS master.

Rename k3s_worker_openstack.json.sample to k3s_worker_openstack.json or create a new file.

To run the script: 

```python
python deploy_k3s_worker_openstack.py
```
---

### 3. deploy_k3s_worker_edge.py
This script Deploys Edge worker node(s) using the AWS master details as input.

#### How to Use:
**Input:** k3s_worker_edge.json + output from AWS master.

Rename k3s_worker_edge.json.sample to k3s_worker_edge.json or create a new file.

To run the script:

```python
python deploy_k3s_worker_edge.py
```
---
Above three script creates a cluster with aws as master, openstack and edge as worker. Login to the master node ansd fetch the k3s deployment using kubectl get nodes.

other scripts are:

### remove_node.py
This script removes a specific node from a cluster.

#### How to Use: Update the CLUSTER_NAME and RESOURCE_NAME variables in the script:

```python
cluster_name = "boring_liskov"
resource_name  = "aws_sweet_swanson"
```
Run the script to remove the node from the cluster.

To run the script: 

```python
python remove_node.py
```

---

### destroy.py
This script destroys an entire cluster, removing all associated nodes and infrastructure.

#### How to Use: Update the CLUSTER_NAME variable:

```python
cluster_name = "quizzical_shamir"
```
Run the script to destroy the cluster. Note: For edge devices, the script will not remove the K3s installation, and you will need to manually uninstall K3s from the edge device.

To run the script: 

```python
python destroy.py
```
---

### deploy_manifests.py
This script deploys Kubernetes manifests to the cluster.

Rename manifest-config.json.sample to manifest-config.json or create a new file.

#### How to Use:
**Input:** manifest-config.json

To run the script: 

```python
python deploy_manifests.py
```

---

### registry.py
This script configures container registry authentication for your cluster.

#### How to Use:
**Input:** It reads credentials from the .env file and updates the cluster accordingly.

Update your .env file with registry credentials (comma-separated lists):

```env
# Registry credentials (comma-separated for multiple)
DOCKER_REGISTRIES=cloud-sztaki.science-cloud.hu,docker.io
DOCKER_USERNAMES=user1,user2
DOCKER_PASSWORDS=pass1,pass2
```

To run the script: 

```python
python registry.py
```

---