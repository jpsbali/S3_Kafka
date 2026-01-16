# Option 1: ECS Fargate with Terraform

## Overview
Serverless container solution using ECS Fargate with:
- DynamoDB checkpointing for resume capability
- Automatic retries and error handling
- CloudWatch logging for monitoring
- Guaranteed delivery with Kafka idempotence

## Architecture
- ECS Fargate Task runs the Python processor
- DynamoDB stores progress (last processed row)
- CloudWatch Logs for monitoring
- IAM roles for S3, DynamoDB, and MSK access

## Deployment

1. Update `terraform.tfvars` with your values
2. Run:
```bash
terraform init
terraform plan
terraform apply
```

3. Start the task:
```bash
aws ecs run-task --cluster csv-to-kafka-cluster --task-definition csv-to-kafka-task --launch-type FARGATE
```

## Recovery
If the task fails, simply restart it. It will resume from the last checkpoint in DynamoDB.

## Monitoring
Check CloudWatch Logs: `/ecs/csv-to-kafka`
Check DynamoDB table: `csv-kafka-checkpoint` for progress
