# Swarmchestrate - Cluster Builder

This repository contains the codebase for **[cluster-builder]**, which builds K3s clusters for Swarmchestrate using OpenTofu.  

The key features of this project include:  
- **Create**: Provisions AWS infrastructure using OpenTofu and installs K3s in high-availability (HA) mode.  
- **Delete**: Destroys the provisioned infrastructure when no longer required. 

---

## Prerequisites

Before proceeding, ensure the following prerequisites are installed:

1. **Git**: For cloning the repository.
2. **Python**: Version 3.7 or higher.
3. **pip**: Python package manager.
4. **AWS CLI**: To manage AWS credentials.
5. **Make**: To run the provided `Makefile`.

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

---

## Running the Code:

 ```bash
python cluster-builder.py
```

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


---