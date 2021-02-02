# TODO: split to several files based on resource type
# TODO: create IAM roles/policies
# TODO: tags to variable

resource "aws_iam_role" "ecs_instance_role" {
  name = "ecs_instance_role"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
    {
        "Action": "sts:AssumeRole",
        "Effect": "Allow",
        "Principal": {
        "Service": "ec2.amazonaws.com"
        }
    }
    ]
}
EOF
  tags = {
    Name = "development"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_instance_role" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance_role" {
  name = "ecs_instance_role"
  role = aws_iam_role.ecs_instance_role.name
}

resource "aws_iam_role" "aws_batch_service_role" {
  name = "aws_batch_service_role"

  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
    {
        "Action": "sts:AssumeRole",
        "Effect": "Allow",
        "Principal": {
        "Service": "batch.amazonaws.com"
        }
    }
    ]
}
EOF

  tags = {
    Name = "development"
  }
}

resource "aws_iam_role_policy_attachment" "aws_batch_service_role" {
  role       = aws_iam_role.aws_batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# For the networking setup, see:
# https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Scenario2.html

resource "aws_vpc" "development" {
  cidr_block = var.vpc_cidr
  tags = {
    Name = "development"
  }
}

resource "aws_eip" "development" {
  vpc = true
  tags = {
    Name = "development"
  }
}

# TODO: this should be an egress-only gateway
resource "aws_internet_gateway" "development" {
  vpc_id = aws_vpc.development.id

  tags = {
    Name = "development"
  }
}

resource "aws_nat_gateway" "development" {
  allocation_id = aws_eip.development.id
  subnet_id     = aws_subnet.development_public.id

  tags = {
    Name = "development"
  }
}

resource "aws_route_table" "development_public" {
  vpc_id = aws_vpc.development.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.development.id
  }

  tags = {
    Name = "development"
  }
}

resource "aws_route_table_association" "development_public" {
  subnet_id      = aws_subnet.development_public.id
  route_table_id = aws_route_table.development_public.id
}

resource "aws_route_table" "development_private" {
  vpc_id = aws_vpc.development.id

  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.development.id
  }

  tags = {
    Name = "development"
  }
}

resource "aws_route_table_association" "development_private" {
  subnet_id      = aws_subnet.development_private.id
  route_table_id = aws_route_table.development_private.id
}

# TODO: we need private/public subnets and gateways per AZ

resource "aws_subnet" "development_private" {
  vpc_id     = aws_vpc.development.id
  cidr_block = var.private_subnet_cidr

  # DEBUG attempt to get rid of this error in Batch:
  # INVALID - CLIENT_ERROR - One or more security groups in the launch 
  # configuration are not linked to the VPCs configured in the Auto 
  # Scaling group

  availability_zone = "us-east-1c"

  tags = {
    Name = "development | private"
  }
}

resource "aws_subnet" "development_public" {
  vpc_id                  = aws_vpc.development.id
  cidr_block              = var.public_subnet_cidr
  map_public_ip_on_launch = true

  # DEBUG. See subnet resource above

  availability_zone = "us-east-1c"

  tags = {
    Name = "development | public"
  }
}

resource "aws_security_group" "batch" {
  name = "batch"
  vpc_id = aws_vpc.development.id

  # TODO: allow SSH ingress from bastion host only

  # All outbound traffic is OK
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "development"
  }
}

# TODO: bastion host for machine access

resource "aws_batch_compute_environment" "development" {
  compute_environment_name = "development8"

  lifecycle {
    # Batch will adapt compute_resources.desired_vcpus depending on queue load,
    # we need to ignore it for TF not to mess with it once it does so.
    ignore_changes = [compute_resources[0].desired_vcpus]
  }

  compute_resources {
    instance_role = aws_iam_instance_profile.ecs_instance_role.arn

    instance_type = [
      "optimal"
    ]

    max_vcpus = var.max_vcpus

    # Be very careful changing min_vcpus. desired_vcpus is set to 0 as TF default,
    # meaning min_vcpus > desired_vcpus, and leading to all manner of strange
    # errors that do not have anything to do with the cpu configuration. If
    # you're changing this number, make sure min_vcpus <= desired_cpus <= max_cpus.

    min_vcpus = var.min_vcpus

    security_group_ids = [
      aws_security_group.batch.id
    ]

    subnets = [
      aws_subnet.development_private.id,
      aws_subnet.development_public.id
    ]

    # TF says this defaults to BEST_FIT, but it does not show in the resulting
    # compute environment.

    allocation_strategy = "BEST_FIT"

    ec2_key_pair = "matthijs"

    type = "EC2"
    tags = {
      Name = "development"
    }
  }

  service_role = aws_iam_role.aws_batch_service_role.arn
  type         = "MANAGED"

  # TODO: we only need to depend on the policy attachment, probably
  depends_on   = [
    aws_iam_role_policy_attachment.aws_batch_service_role,
    aws_nat_gateway.development,
    aws_internet_gateway.development
  ]
  tags = {
    Name = "development"
  }
}

resource "aws_batch_job_queue" "development" {
  name     = "development"
  state    = "ENABLED"
  priority = 1
  compute_environments = [
    aws_batch_compute_environment.development.arn
  ]
  tags = {
    Name = "development"
  }
}

resource "aws_batch_job_definition" "development" {
  name = "development"
  type = "container"

  container_properties = <<EOF
{
    "command": ["echo", "hello"],
    "image": "busybox",
    "memory": 512,
    "vcpus": 1
}
EOF
}