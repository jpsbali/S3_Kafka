variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "s3_bucket" {
  description = "S3 bucket containing the CSV file"
  type        = string
}

variable "s3_key" {
  description = "S3 key (path) to the CSV file"
  type        = string
}

variable "kafka_bootstrap_servers" {
  description = "Kafka bootstrap servers (comma-separated)"
  type        = string
}

variable "kafka_topic" {
  description = "Kafka topic name"
  type        = string
}

variable "msk_cluster_arn" {
  description = "ARN of the MSK cluster"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where ECS task will run"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for ECS task (private subnets with NAT gateway)"
  type        = list(string)
}

variable "task_cpu" {
  description = "CPU units for the task (1024 = 1 vCPU)"
  type        = string
  default     = "2048"
}

variable "task_memory" {
  description = "Memory for the task in MB"
  type        = string
  default     = "4096"
}

variable "job_id" {
  description = "Unique job identifier for checkpointing"
  type        = string
  default     = "csv-job-1"
}
