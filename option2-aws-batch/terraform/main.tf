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
  name           = "csv-kafka-checkpoint-batch"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "job_id"

  attribute {
    name = "job_id"
    type = "S"
  }

  tags = {
    Name = "CSV to Kafka Checkpoint (Batch)"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "batch_logs" {
  name              = "/aws/batch/csv-to-kafka"
  retention_in_days = 7
}

# IAM Role for Batch Job
resource "aws_iam_role" "batch_job_role" {
  name = "csv-kafka-batch-job-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

# IAM Policy for Batch Job
resource "aws_iam_role_policy" "batch_job_policy" {
  name = "csv-kafka-batch-policy"
  role = aws_iam_role.batch_job_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket}",
          "arn:aws:s3:::${var.s3_bucket}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.checkpoint.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kafka-cluster:*"
        ]
        Resource = "${var.msk_cluster_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "CSVToKafka"
          }
        }
      }
    ]
  })
}

# ECR Repository
resource "aws_ecr_repository" "app" {
  name                 = "csv-to-kafka-batch"
  image_tag_mutability = "MUTABLE"
}

# Batch Compute Environment
resource "aws_batch_compute_environment" "spot" {
  compute_environment_name = "csv-kafka-spot-env"
  type                     = "MANAGED"
  service_role             = aws_iam_role.batch_service_role.arn

  compute_resources {
    type               = "SPOT"
    allocation_strategy = "SPOT_CAPACITY_OPTIMIZED"
    bid_percentage     = 100
    max_vcpus          = 4
    min_vcpus          = 0
    desired_vcpus      = 0
    
    instance_type = ["optimal"]
    
    subnets         = var.subnet_ids
    security_group_ids = [aws_security_group.batch.id]
    
    instance_role = aws_iam_instance_profile.ecs_instance.arn
  }
}

# Batch Service Role
resource "aws_iam_role" "batch_service_role" {
  name = "csv-kafka-batch-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "batch.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "batch_service_role" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# ECS Instance Role
resource "aws_iam_role" "ecs_instance_role" {
  name = "csv-kafka-ecs-instance-role"

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

resource "aws_iam_role_policy_attachment" "ecs_instance_role" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance" {
  name = "csv-kafka-ecs-instance-profile"
  role = aws_iam_role.ecs_instance_role.name
}

# Security Group
resource "aws_security_group" "batch" {
  name        = "csv-kafka-batch-sg"
  description = "Security group for Batch jobs"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Batch Job Queue
resource "aws_batch_job_queue" "main" {
  name     = "csv-kafka-job-queue"
  state    = "ENABLED"
  priority = 1

  compute_environments = [
    aws_batch_compute_environment.spot.arn
  ]
}

# Batch Job Definition
resource "aws_batch_job_definition" "main" {
  name = "csv-kafka-job-def"
  type = "container"

  platform_capabilities = ["EC2"]

  container_properties = jsonencode({
    image = "${aws_ecr_repository.app.repository_url}:latest"
    
    jobRoleArn = aws_iam_role.batch_job_role.arn
    
    resourceRequirements = [
      {
        type  = "VCPU"
        value = "2"
      },
      {
        type  = "MEMORY"
        value = "4096"
      }
    ]
    
    environment = [
      {
        name  = "S3_BUCKET"
        value = var.s3_bucket
      },
      {
        name  = "S3_KEY"
        value = var.s3_key
      },
      {
        name  = "KAFKA_BOOTSTRAP_SERVERS"
        value = var.kafka_bootstrap_servers
      },
      {
        name  = "KAFKA_TOPIC"
        value = var.kafka_topic
      },
      {
        name  = "DYNAMODB_TABLE"
        value = aws_dynamodb_table.checkpoint.name
      },
      {
        name  = "JOB_ID"
        value = var.job_id
      }
    ]
    
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.batch_logs.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "batch"
      }
    }
  })

  retry_strategy {
    attempts = 3
  }

  timeout {
    attempt_duration_seconds = 43200  # 12 hours
  }
}
