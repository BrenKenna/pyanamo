# AWS MinE Terraform modules
[Terraform](https://www.terraform.io/) files to deploy a Batch environment, job queue and dependencies. Single-AZ setup, the networking and IAM bits could do with a bit of work.

## Bootstrapping
Bootstrap an S3 bucket and DynamoDB table for use as a Terraform backend:

```bash
./bootstrap
```

## Terraforming
Inspect the execution plan with and sanity-check it for errors:

```bash
terraform plan -var-file development.tfvars
```

Apply the execution plan to create or update resources on AWS:

```bash
terraform apply -var-file development.tfvars
```

## Issues
* Sometimes compute environments do not want to be deleted because they are both being deleted and being modified (apparently). So far there does not appear to be a way to resolve this.
* Launch configurations and autoscaling groups are created only when the desired number of vCPUs > 0
* Job scheduling frequency seems to be around 30 seconds, meaning jobs with a (much) shorter runtime will use the cluster inefficiently
