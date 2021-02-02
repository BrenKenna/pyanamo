variable "region" {
  type = string
  description = "AWS region"
  default = "us-east-1"
}

variable "private_subnet_cidr" {
  type = string
  description = "CIDR for private subnet"
  default = "10.0.1.0/24"
}

variable "public_subnet_cidr" {
  type = string
  description = "CIDR for private subnet"
  default = "10.0.0.0/24"
}

variable "vpc_cidr" {
  type = string
  description = "CIDR for VPC"
  default = "10.0.0.0/16"
}

variable "min_vcpus" {
  type = number
  description = "Minimum number of vCPUs in compute environment"
  default = 0
}

variable "max_vcpus" {
  type = number
  description = "Maximum number of vCPUs in compute environment"
  default = 4
}
