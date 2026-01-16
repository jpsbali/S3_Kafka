# Option 2: AWS Batch with Spot Instances

## Overview
Cost-optimized solution using AWS Batch with Spot instances:
- Up to 90% cost savings with Spot instances
- Automatic retry on Spot interruption
- DynamoDB checkpointing for resume capability
- Managed job scheduling and execution

## Architecture
- AWS Batch Job Definition and Compute Environment
- Spot instances for cost optimization
- DynamoDB for checkpointing
- CloudWatch for logging
- Automatic failover to on-demand if Spot unavailable

## Deployment

1. Update `terraform.tfvars` with your values
2. Run:
```bash
terraform init
terraform plan
terraform apply
```

3. Submit the job:
```bash
aws batch submit-job \
  --job-name csv-to-kafka-job \
  --job-queue csv-kafka-job-queue \
  --job-definition csv-kafka-job-def
```

## Cost Estimate
For 100M rows (~2-3 hour job):
- Spot instance (4 vCPU, 8GB): ~$0.10-0.30
- DynamoDB: ~$0.01
- Total: < $0.50

## Recovery
AWS Batch automatically retries failed jobs. Checkpointing ensures no data loss.
