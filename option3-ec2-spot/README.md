# Option 3: EC2 Spot Instance

## Overview
Simplest and most cost-effective solution using EC2 Spot instances:
- Up to 90% cost savings with Spot pricing
- Self-terminating after completion
- DynamoDB checkpointing for recovery
- User-data script handles everything

## Architecture
- Single EC2 Spot instance
- User-data script installs dependencies and runs processor
- Instance terminates automatically when complete
- DynamoDB for checkpointing

## Deployment

### Option A: Using Terraform

1. Update `terraform.tfvars` with your values
2. Run:
```bash
cd terraform
terraform init
terraform apply
```

3. Launch instance:
```bash
aws ec2 run-instances \
  --launch-template LaunchTemplateId=<from-output> \
  --instance-market-options '{"MarketType":"spot","SpotOptions":{"MaxPrice":"0.05","SpotInstanceType":"one-time"}}'
```

### Option B: Manual Launch (No Terraform)

1. Edit `user-data.sh` with your configuration values
2. Launch via AWS Console or CLI:

```bash
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --iam-instance-profile Name=csv-kafka-ec2-profile \
  --user-data file://user-data.sh \
  --instance-market-options '{"MarketType":"spot","SpotOptions":{"MaxPrice":"0.05"}}' \
  --subnet-id subnet-xxxxx \
  --security-group-ids sg-xxxxx
```

## Cost Estimate
For 100M rows (~2-3 hour job):
- Spot instance (t3.medium): ~$0.01-0.03
- DynamoDB: ~$0.01
- Total: < $0.05

## Recovery
If Spot instance is interrupted, simply launch a new one. It will resume from the last checkpoint.

## Monitoring
Check logs: `/var/log/csv-processor.log` on the instance
Check DynamoDB table for progress
