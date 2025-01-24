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

### 4. Configuring AWS Credentials

Set up your AWS credentials using the AWS CLI:

 ```bash
 aws configure
```

When prompted, provide the following details:
- AWS Access Key ID
- AWS Secret Access Key
- Default region name (e.g., eu-west-2)
- Default output format (leave blank or use json)

### 5. Configuring Terraform Variables
Update the terraform.tfvars file to define your AWS infrastructure parameters. Below is an example configuration:

 ```bash
aws_region    = "eu-west-2"        # London region
instance_type = "t2.micro"         # EC2 instance type
ssh_key_name  = "my-ssh-key"       # AWS key pair name
k3s_token     = "my-secret-token"  # K3s cluster token

ami             = "ami-0c0493bbac867d427"  # Amazon Machine Image
ha_server_count = 2                        # High-availability server count
```

Ensure the following:
- The AMI ID matches a valid AMI in the specified AWS region.
- The AWS region is correct.
- The SSH key name corresponds to a key pair in your AWS account.

---

## Running the Code:

 ```bash
python cluster-builder.py
```