#!/bin/bash
set -e

# Simple script to launch EC2 Spot instance

# Configuration
INSTANCE_TYPE="t3.medium"
MAX_SPOT_PRICE="0.05"
SUBNET_ID="subnet-xxxxx"  # Replace with your subnet
SECURITY_GROUP="sg-xxxxx"  # Replace with your security group
IAM_PROFILE="csv-kafka-ec2-profile"
AMI_ID="ami-0c55b159cbfafe1f0"  # Amazon Linux 2 (update for your region)

echo "Launching EC2 Spot instance..."

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type $INSTANCE_TYPE \
  --iam-instance-profile Name=$IAM_PROFILE \
  --user-data file://user-data.sh \
  --instance-market-options "{\"MarketType\":\"spot\",\"SpotOptions\":{\"MaxPrice\":\"$MAX_SPOT_PRICE\",\"SpotInstanceType\":\"one-time\"}}" \
  --subnet-id $SUBNET_ID \
  --security-group-ids $SECURITY_GROUP \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=csv-to-kafka-processor}]' \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Instance launched: $INSTANCE_ID"
echo "Monitor progress:"
echo "  aws ec2 describe-instances --instance-ids $INSTANCE_ID"
echo "  aws dynamodb get-item --table-name csv-kafka-checkpoint-ec2 --key '{\"job_id\":{\"S\":\"csv-job-1\"}}'"
