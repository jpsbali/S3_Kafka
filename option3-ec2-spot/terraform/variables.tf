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
  description = "VPC ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for EC2 instance"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "job_id" {
  description = "Unique job identifier"
  type        = string
  default     = "csv-job-1"
}
