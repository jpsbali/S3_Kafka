terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# DynamoDB table for checkpointing
resource "aws_dynamodb_table" "checkpoint" {
  name           = "csv-kafka-checkpoint-ec2"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "job_id"

  attribute {
    name = "job_id"
    type = "S"
  }
}

# IAM Role for EC2
resource "aws_iam_role" "ec2_role" {
  name = "csv-kafka-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "ec2_policy" {
  name = "csv-kafka-ec2-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket}",
          "arn:aws:s3:::${var.s3_bucket}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = ["dynamodb:*"]
        Resource = aws_dynamodb_table.checkpoint.arn
      },
      {
        Effect = "Allow"
        Action = ["kafka-cluster:*"]
        Resource = "${var.msk_cluster_arn}/*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "csv-kafka-ec2-profile"
  role = aws_iam_role.ec2_role.name
}


# Security Group
resource "aws_security_group" "ec2_sg" {
  name        = "csv-kafka-ec2-sg"
  description = "Security group for CSV processor EC2"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Launch Template for Spot Instance
resource "aws_launch_template" "spot" {
  name_prefix   = "csv-kafka-spot-"
  image_id      = data.aws_ami.amazon_linux_2.id
  instance_type = var.instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2_profile.name
  }

  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  user_data = base64encode(templatefile("${path.module}/../user-data.sh", {
    S3_BUCKET               = var.s3_bucket
    S3_KEY                  = var.s3_key
    KAFKA_BOOTSTRAP_SERVERS = var.kafka_bootstrap_servers
    KAFKA_TOPIC             = var.kafka_topic
    DYNAMODB_TABLE          = aws_dynamodb_table.checkpoint.name
    JOB_ID                  = var.job_id
    AWS_REGION              = var.aws_region
  }))

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "csv-to-kafka-processor"
    }
  }
}

# Get latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}
