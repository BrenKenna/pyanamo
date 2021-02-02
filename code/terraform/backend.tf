terraform {
  backend "s3" {
    bucket         = "terraform-remote-state-storage-mine"
    key            = "terraform/state/mine/terraform.tfstate"
    region         = "us-east-1"  # can't use var.region here, cause Terraform
    encrypt        = true
    dynamodb_table = "terraform-lock-table"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "3.21.0"
    }
  }
}
