# Adding a New Cloud Provider

This document outlines the process for adding support for new cloud providers to the Cluster Builder project.

## Table of Contents

- [Adding a New Cloud Provider](#adding-a-new-cloud-provider)
  - [1. Create Provider Templates](#1-create-provider-templates)
  - [2. Update Environment Examples](#2-update-environment-examples)
- [Code Style Guidelines](#code-style-guidelines)

## Adding a New Cloud Provider

### 1. Create Provider Templates

In the `templates/` directory, create the following files for your cloud provider (replace `PROVIDER` with the lowercase name of your provider, e.g., `aws`, `gcp`, `azure`):

#### a. Provider Configuration (`PROVIDER_provider.tf`)

Create a Terraform file with the provider configuration and required variables:

```hcl
# Provider configuration for PROVIDER
provider "PROVIDER" {
  # Example provider-specific configuration
  client_id     = var.PROVIDER_client_id
  client_secret = var.PROVIDER_client_secret
}

# The provider-specific variables are based on your provider's requirements

# Variable definition
variable "PROVIDER_client_id" {
  description = "Client ID for PROVIDER authentication"
  type        = string
  sensitive   = true
}

variable "PROVIDER_client_secret" {
  description = "Client secret for PROVIDER authentication"
  type        = string
  sensitive   = true
}

# Add more provider-specific variables as needed
```

#### b. Update Environment Examples

Add the new provider's required variables to the `.env_example` file. They
are your variable names, prefixed by `TF_VAR_`.

```
# PROVIDER Variables
TF_VAR_PROVIDER_client_id=your_client_id
TF_VAR_PROVIDER_client_secret=your_client_secret
```

These are used during deployment with an actual `.env` file.

#### c. Main Template (`PROVIDER/main.tf`)

Create a directory for your provider and add a `main.tf` file with the necessary resources:

```hcl
# variables.tf section
variable "cluster_name" {}
variable "resource_name" {}
variable "k3s_role" {}
variable "master_ip" {
  default = null
}
# Add provider-specific variables

# main.tf section
resource "PROVIDER_instance" "k3s_node" {
  # Provider-specific configuration
  
}

# Add provider-specific resources like security groups, networks, etc.

# outputs.tf section should at least include:
output "cluster_name" {
  value = var.k3s_role == "master" ? var.cluster_name : null
}

output "master_ip" {
  value = var.k3s_role == "master" ? PROVIDER_instance.k3s_node.public_ip : null
}
```
