# Operations Guide

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Procedures](#deployment-procedures)
3. [Running Jobs](#running-jobs)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Recovery Procedures](#recovery-procedures)
7. [Maintenance](#maintenance)
8. [Cost Management](#cost-management)

---

## Pre-Deployment Checklist

### AWS Prerequisites

- [ ] AWS Account with appropriate permissions
- [ ] AWS CLI installed and configured
- [ ] Terraform installed (v1.0+)
- [ ] Docker installed (for ECS/Batch options)
- [ ] VPC with private subnets and NAT gateway
- [ ] Amazon MSK cluster running and accessible
- [ ] S3 bucket with CSV file uploaded

### Network Requirements

- [ ] Private subnets have route to NAT gateway
- [ ] NAT gateway has route to Internet Gateway
- [ ] Security groups allow egress to:
  - S3 (HTTPS/443)
  - DynamoDB (HTTPS/443)
  - MSK (9092, 9094)
  - CloudWatch (HTTPS/443)

### IAM Permissions Required

**For Deployment (Terraform):**
- `iam:CreateRole`, `iam:AttachRolePolicy`
- `ec2:CreateSecurityGroup`, `ec2:AuthorizeSecurityGroupEgress`
- `ecs:CreateCluster`, `ecs:RegisterTaskDefinition` (ECS)
- `batch:CreateComputeEnvironment`, `batch:CreateJobQueue` (Batch)
- `dynamodb:CreateTable`
- `ecr:CreateRepository`
- `logs:CreateLogGroup`

**For Execution (Application):**
- `s3:GetObject`, `s3:ListBucket`
- `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:UpdateItem`
- `kafka-cluster:Connect`, `kafka-cluster:WriteData`

### Kafka/MSK Requirements

- [ ] MSK cluster is running
- [ ] Topic exists (or auto-create enabled)
- [ ] Topic has at least 1 partition
- [ ] Replication factor ≥ 2 (recommended)
- [ ] Security group allows connections from processor
- [ ] Authentication configured (if using IAM auth)

---

## Deployment Procedures

### Option 1: ECS Fargate Deployment

#### Step 1: Configure Variables

```bash
cd option1-ecs-fargate/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region              = "us-east-1"
s3_bucket               = "my-data-bucket"
s3_key                  = "exports/data.csv"
kafka_bootstrap_servers = "b-1.msk.us-east-1.amazonaws.com:9092,b-2.msk.us-east-1.amazonaws.com:9092"
kafka_topic             = "csv-import"
msk_cluster_arn         = "arn:aws:kafka:us-east-1:123456789012:cluster/my-cluster/abc123"
vpc_id                  = "vpc-0123456789abcdef0"
subnet_ids              = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
```

#### Step 2: Deploy Infrastructure

```bash
terraform init
terraform plan  # Review changes
terraform apply
```

Save outputs:
```bash
terraform output ecr_repository_url > ../ecr_url.txt
```

#### Step 3: Build and Push Docker Image

```bash
cd ../app

# Get ECR URL
ECR_REPO=$(cat ../ecr_url.txt)
AWS_REGION="us-east-1"

# Build image
docker build -t csv-to-kafka:latest .

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REPO

# Tag and push
docker tag csv-to-kafka:latest $ECR_REPO:latest
docker push $ECR_REPO:latest
```

#### Step 4: Verify Deployment

```bash
# Check ECS cluster
aws ecs describe-clusters --clusters csv-to-kafka-cluster

# Check task definition
aws ecs describe-task-definition --task-definition csv-to-kafka-task

# Check DynamoDB table
aws dynamodb describe-table --table-name csv-kafka-checkpoint
```

### Option 2: AWS Batch Deployment

Follow similar steps as ECS Fargate, but use `option2-aws-batch` directory.

#### Additional Step: Verify Batch Resources

```bash
# Check compute environment
aws batch describe-compute-environments \
  --compute-environments csv-kafka-spot-env

# Check job queue
aws batch describe-job-queues --job-queues csv-kafka-job-queue

# Check job definition
aws batch describe-job-definitions --job-definitions csv-kafka-job-def
```

### Option 3: EC2 Spot Deployment

#### Option A: Using Terraform

```bash
cd option3-ec2-spot/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars
terraform init
terraform apply
```

#### Option B: Manual Launch

```bash
cd option3-ec2-spot

# Edit user-data.sh with your configuration
vim user-data.sh

# Launch instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --iam-instance-profile Name=csv-kafka-ec2-profile \
  --user-data file://user-data.sh \
  --instance-market-options '{"MarketType":"spot","SpotOptions":{"MaxPrice":"0.05","SpotInstanceType":"one-time"}}' \
  --subnet-id subnet-xxxxx \
  --security-group-ids sg-xxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=csv-to-kafka-processor}]'
```

---

## Running Jobs

### ECS Fargate: Run Task

#### Using AWS CLI

```bash
aws ecs run-task \
  --cluster csv-to-kafka-cluster \
  --task-definition csv-to-kafka-task \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=DISABLED}"
```

#### Using AWS Console

1. Navigate to ECS → Clusters → csv-to-kafka-cluster
2. Click "Tasks" tab
3. Click "Run new task"
4. Select:
   - Launch type: Fargate
   - Task definition: csv-to-kafka-task
   - VPC, subnets, security group
5. Click "Run task"

### AWS Batch: Submit Job

#### Using AWS CLI

```bash
aws batch submit-job \
  --job-name csv-kafka-job-$(date +%s) \
  --job-queue csv-kafka-job-queue \
  --job-definition csv-kafka-job-def
```

#### Using AWS Console

1. Navigate to AWS Batch → Jobs
2. Click "Submit new job"
3. Select:
   - Job name: csv-kafka-job-1
   - Job definition: csv-kafka-job-def
   - Job queue: csv-kafka-job-queue
4. Click "Submit job"

### EC2 Spot: Launch Instance

Already covered in deployment section. Instance starts processing automatically.

---

## Monitoring

### Real-Time Progress Monitoring

#### Check DynamoDB Checkpoint

```bash
# Get current progress
aws dynamodb get-item \
  --table-name csv-kafka-checkpoint \
  --key '{"job_id":{"S":"csv-job-1"}}' \
  --output json | jq '.Item'

# Output:
# {
#   "job_id": {"S": "csv-job-1"},
#   "last_line": {"N": "50000"},
#   "total_sent": {"N": "50000"},
#   "timestamp": {"N": "1705420800"}
# }
```

#### Watch Progress (Poll Every 10 Seconds)

```bash
watch -n 10 'aws dynamodb get-item \
  --table-name csv-kafka-checkpoint \
  --key "{\"job_id\":{\"S\":\"csv-job-1\"}}" \
  --query "Item.{Line:last_line.N,Sent:total_sent.N,Time:timestamp.N}" \
  --output table'
```

### CloudWatch Logs

#### ECS Fargate Logs

```bash
# Tail logs
aws logs tail /ecs/csv-to-kafka --follow

# Get specific task logs
aws logs tail /ecs/csv-to-kafka --follow \
  --log-stream-names ecs/csv-processor/<task-id>

# Search for errors
aws logs filter-log-events \
  --log-group-name /ecs/csv-to-kafka \
  --filter-pattern "ERROR"
```

#### AWS Batch Logs

```bash
# Tail logs
aws logs tail /aws/batch/csv-to-kafka --follow

# Get specific job logs
aws logs tail /aws/batch/csv-to-kafka --follow \
  --log-stream-names batch/csv-processor/<job-id>
```

#### EC2 Instance Logs

```bash
# SSH to instance
ssh -i your-key.pem ec2-user@<instance-ip>

# View logs
tail -f /var/log/csv-processor.log

# Search for errors
grep ERROR /var/log/csv-processor.log
```

### Task/Job Status

#### ECS Task Status

```bash
# List running tasks
aws ecs list-tasks --cluster csv-to-kafka-cluster

# Describe task
aws ecs describe-tasks \
  --cluster csv-to-kafka-cluster \
  --tasks <task-arn>
```

#### Batch Job Status

```bash
# List jobs
aws batch list-jobs --job-queue csv-kafka-job-queue

# Describe job
aws batch describe-jobs --jobs <job-id>
```

#### EC2 Instance Status

```bash
# List instances
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=csv-to-kafka-processor" \
  --query "Reservations[].Instances[].[InstanceId,State.Name,LaunchTime]" \
  --output table
```

### Kafka Topic Verification

```bash
# Check topic offset (total records)
kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list $KAFKA_BROKERS \
  --topic csv-import \
  --time -1

# Output: csv-import:0:100000000
# (topic:partition:offset)

# Consume last 10 records
kafka-console-consumer \
  --bootstrap-server $KAFKA_BROKERS \
  --topic csv-import \
  --partition 0 \
  --offset -10 \
  --max-messages 10
```

---

## Troubleshooting

### Common Issues

#### Issue: Task/Job Won't Start

**Symptoms:**
- Task stuck in PENDING state
- Job stuck in RUNNABLE state

**Diagnosis:**
```bash
# Check task/job status
aws ecs describe-tasks --cluster csv-to-kafka-cluster --tasks <task-arn>
aws batch describe-jobs --jobs <job-id>

# Check for error messages in stoppedReason or statusReason
```

**Common Causes:**
1. **No available compute resources**
   - Solution: Wait or increase max vCPUs (Batch)

2. **Image pull error**
   - Solution: Verify ECR repository exists and has image
   ```bash
   aws ecr describe-images --repository-name csv-to-kafka
   ```

3. **IAM permission error**
   - Solution: Check execution role has ECR permissions

4. **Network error**
   - Solution: Verify subnets have NAT gateway route

#### Issue: Processing Stops Mid-Run

**Symptoms:**
- Checkpoint not updating
- No new logs
- Task/job shows as STOPPED/FAILED

**Diagnosis:**
```bash
# Check last checkpoint
aws dynamodb get-item \
  --table-name csv-kafka-checkpoint \
  --key '{"job_id":{"S":"csv-job-1"}}'

# Check CloudWatch logs for errors
aws logs filter-log-events \
  --log-group-name /ecs/csv-to-kafka \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Common Causes:**
1. **Kafka broker unavailable**
   - Check MSK cluster health
   - Check security groups
   - Solution: Fix Kafka, restart job

2. **Network interruption**
   - Check VPC flow logs
   - Solution: Restart job (will resume from checkpoint)

3. **Out of memory**
   - Check CloudWatch metrics
   - Solution: Increase task memory

4. **Spot interruption** (Batch/EC2)
   - Check EC2 Spot interruption logs
   - Solution: Restart job (Batch auto-retries)

#### Issue: Records Not in Kafka

**Symptoms:**
- Checkpoint shows progress
- Kafka topic offset is 0 or low

**Diagnosis:**
```bash
# Check Kafka topic
kafka-topics --bootstrap-server $KAFKA_BROKERS --describe --topic csv-import

# Check producer logs
aws logs filter-log-events \
  --log-group-name /ecs/csv-to-kafka \
  --filter-pattern "sent to partition"
```

**Common Causes:**
1. **Wrong topic name**
   - Solution: Verify KAFKA_TOPIC environment variable

2. **Kafka security group blocking**
   - Solution: Add processor security group to MSK ingress rules

3. **Authentication failure**
   - Solution: Configure IAM auth correctly

#### Issue: Checkpoint Not Updating

**Symptoms:**
- DynamoDB item not changing
- Logs show progress but checkpoint stale

**Diagnosis:**
```bash
# Check DynamoDB table
aws dynamodb describe-table --table-name csv-kafka-checkpoint

# Check IAM permissions
aws iam get-role-policy \
  --role-name csv-kafka-ecs-task-role \
  --policy-name csv-kafka-task-policy
```

**Common Causes:**
1. **DynamoDB permission error**
   - Solution: Add dynamodb:PutItem permission to task role

2. **Wrong table name**
   - Solution: Verify DYNAMODB_TABLE environment variable

3. **DynamoDB throttling** (unlikely with on-demand)
   - Solution: Check CloudWatch metrics

---

## Recovery Procedures

### Scenario 1: Process Crashed Mid-Run

**Steps:**
1. Check last checkpoint:
   ```bash
   aws dynamodb get-item \
     --table-name csv-kafka-checkpoint \
     --key '{"job_id":{"S":"csv-job-1"}}'
   ```

2. Verify Kafka offset matches checkpoint:
   ```bash
   kafka-run-class kafka.tools.GetOffsetShell \
     --broker-list $KAFKA_BROKERS \
     --topic csv-import \
     --time -1
   ```

3. Restart job with same job_id:
   ```bash
   # ECS
   aws ecs run-task --cluster csv-to-kafka-cluster --task-definition csv-to-kafka-task ...
   
   # Batch
   aws batch submit-job --job-name csv-kafka-job --job-queue csv-kafka-job-queue ...
   
   # EC2
   # Launch new instance with same JOB_ID in user-data
   ```

4. Monitor resume:
   ```bash
   aws logs tail /ecs/csv-to-kafka --follow | grep "Starting from line"
   ```

### Scenario 2: Kafka Cluster Failure

**Steps:**
1. Stop current job (if running):
   ```bash
   # ECS
   aws ecs stop-task --cluster csv-to-kafka-cluster --task <task-arn>
   
   # Batch
   aws batch terminate-job --job-id <job-id> --reason "Kafka unavailable"
   ```

2. Fix Kafka cluster

3. Verify Kafka is healthy:
   ```bash
   kafka-broker-api-versions --bootstrap-server $KAFKA_BROKERS
   ```

4. Restart job (will resume from checkpoint)

### Scenario 3: Wrong Data Sent to Kafka

**Steps:**
1. Stop current job immediately

2. Check checkpoint to see how many records were sent:
   ```bash
   aws dynamodb get-item \
     --table-name csv-kafka-checkpoint \
     --key '{"job_id":{"S":"csv-job-1"}}'
   ```

3. Delete records from Kafka (if possible):
   ```bash
   # Option 1: Delete topic and recreate
   kafka-topics --bootstrap-server $KAFKA_BROKERS --delete --topic csv-import
   kafka-topics --bootstrap-server $KAFKA_BROKERS --create --topic csv-import --partitions 1 --replication-factor 2
   
   # Option 2: Use retention to expire records
   kafka-configs --bootstrap-server $KAFKA_BROKERS \
     --entity-type topics --entity-name csv-import \
     --alter --add-config retention.ms=1000
   ```

4. Delete checkpoint:
   ```bash
   aws dynamodb delete-item \
     --table-name csv-kafka-checkpoint \
     --key '{"job_id":{"S":"csv-job-1"}}'
   ```

5. Fix configuration issue

6. Restart job from beginning

### Scenario 4: Need to Restart from Specific Line

**Steps:**
1. Update checkpoint manually:
   ```bash
   aws dynamodb put-item \
     --table-name csv-kafka-checkpoint \
     --item '{
       "job_id": {"S": "csv-job-1"},
       "last_line": {"N": "50000"},
       "total_sent": {"N": "50000"},
       "timestamp": {"N": "'$(date +%s)'"}
     }'
   ```

2. Restart job (will resume from line 50001)

---

## Maintenance

### Regular Tasks

#### Daily
- [ ] Check for failed jobs/tasks
- [ ] Review CloudWatch logs for errors
- [ ] Verify checkpoint updates for running jobs

#### Weekly
- [ ] Review AWS costs
- [ ] Check DynamoDB table for stuck jobs
- [ ] Review Kafka topic lag
- [ ] Clean up old CloudWatch log streams

#### Monthly
- [ ] Update Python dependencies
- [ ] Review and update Terraform modules
- [ ] Test recovery procedures
- [ ] Review security group rules

### Updating Dependencies

#### Python Packages

```bash
cd option1-ecs-fargate/app  # or option2-aws-batch/app

# Update requirements.txt
pip install --upgrade boto3 kafka-python smart-open
pip freeze > requirements.txt

# Rebuild and push image
docker build -t csv-to-kafka:latest .
docker tag csv-to-kafka:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# Update task definition (ECS)
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Update job definition (Batch)
aws batch register-job-definition --cli-input-json file://job-definition.json
```

#### Terraform Updates

```bash
cd option1-ecs-fargate/terraform

# Update provider versions in main.tf
terraform init -upgrade

# Review changes
terraform plan

# Apply updates
terraform apply
```

### Cleanup

#### Remove Old Checkpoints

```bash
# List all checkpoints
aws dynamodb scan --table-name csv-kafka-checkpoint

# Delete specific checkpoint
aws dynamodb delete-item \
  --table-name csv-kafka-checkpoint \
  --key '{"job_id":{"S":"old-job-id"}}'
```

#### Remove Old Log Streams

```bash
# List log streams
aws logs describe-log-streams \
  --log-group-name /ecs/csv-to-kafka \
  --order-by LastEventTime \
  --descending

# Delete old log stream
aws logs delete-log-stream \
  --log-group-name /ecs/csv-to-kafka \
  --log-stream-name <stream-name>
```

#### Remove Old ECR Images

```bash
# List images
aws ecr list-images --repository-name csv-to-kafka

# Delete old image
aws ecr batch-delete-image \
  --repository-name csv-to-kafka \
  --image-ids imageTag=old-tag
```

---

## Cost Management

### Monitoring Costs

#### AWS Cost Explorer

1. Navigate to AWS Cost Explorer
2. Filter by:
   - Service: ECS, Batch, EC2, DynamoDB, CloudWatch
   - Tag: Add tags to resources for tracking

#### Cost Breakdown

```bash
# Get cost for last 30 days
aws ce get-cost-and-usage \
  --time-period Start=2026-01-01,End=2026-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

### Cost Optimization Tips

1. **Use Spot Instances** (Batch/EC2)
   - 70-90% cost savings
   - Acceptable for batch workloads

2. **Right-size Resources**
   - Start with t3.medium or 2 vCPU
   - Monitor CPU/memory usage
   - Adjust if needed

3. **Optimize Checkpoint Interval**
   - Fewer checkpoints = fewer DynamoDB writes
   - Trade-off: longer recovery time

4. **Use CloudWatch Logs Retention**
   - Set retention to 7 days (default)
   - Reduce to 1 day if not needed

5. **Clean Up Resources**
   - Delete old checkpoints
   - Remove old ECR images
   - Delete old log streams

### Cost Alerts

```bash
# Create budget alert
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

**budget.json:**
```json
{
  "BudgetName": "CSV-Kafka-Monthly",
  "BudgetLimit": {
    "Amount": "10",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

---

## Appendix

### Useful Commands Reference

```bash
# ECS
aws ecs list-clusters
aws ecs list-tasks --cluster csv-to-kafka-cluster
aws ecs describe-tasks --cluster csv-to-kafka-cluster --tasks <task-arn>
aws ecs stop-task --cluster csv-to-kafka-cluster --task <task-arn>

# Batch
aws batch list-jobs --job-queue csv-kafka-job-queue
aws batch describe-jobs --jobs <job-id>
aws batch terminate-job --job-id <job-id> --reason "Manual stop"

# EC2
aws ec2 describe-instances --filters "Name=tag:Name,Values=csv-to-kafka-processor"
aws ec2 terminate-instances --instance-ids <instance-id>

# DynamoDB
aws dynamodb get-item --table-name csv-kafka-checkpoint --key '{"job_id":{"S":"csv-job-1"}}'
aws dynamodb scan --table-name csv-kafka-checkpoint
aws dynamodb delete-item --table-name csv-kafka-checkpoint --key '{"job_id":{"S":"csv-job-1"}}'

# CloudWatch
aws logs tail /ecs/csv-to-kafka --follow
aws logs filter-log-events --log-group-name /ecs/csv-to-kafka --filter-pattern "ERROR"

# Kafka
kafka-topics --bootstrap-server $KAFKA_BROKERS --list
kafka-topics --bootstrap-server $KAFKA_BROKERS --describe --topic csv-import
kafka-run-class kafka.tools.GetOffsetShell --broker-list $KAFKA_BROKERS --topic csv-import --time -1
```

---

**Document Version:** 1.0.0  
**Last Updated:** January 16, 2026
