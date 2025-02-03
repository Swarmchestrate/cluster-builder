# AWS Variables
variable "aws_region" {
  description = "The AWS region to deploy resources in"
  type        = string
  default     = "eu-west-2" # Default region is London
}

variable "ami" {
  description = "The type of EC2 instance"
  type        = string
  default     = "ami-0c0493bbac867d427"
}

variable "instance_type" {
  description = "The type of EC2 instance"
  type        = string
  default     = "t2.micro"
}

variable "ssh_key_name" {
  description = "The name of the SSH key pair to use for EC2"
  type        = string
}

variable "aws_ha_server_count" {
  description = "Number of EC2 instances to create"
  type        = number
  default     = 1
}

variable "aws_worker_count" {
  description = "Number of EC2 instances to create"
  type        = number
  default     = 1
}

variable "master_ip" {
  description = "Number of EC2 instances to create"
  type        = string
}

variable "cluster_name" {
  description = "The cluster name for all nodes"
  type        = string
}