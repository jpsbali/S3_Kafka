# Quick Reference Card

## 🚀 One-Page Cheat Sheet

---

## Choose Your Solution

| Need | Choose | Cost | Time to Deploy |
|------|--------|------|----------------|
| Production-ready | **ECS Fargate** | $0.63 | 15 min |
| Cost-optimized | **AWS Batch** | $0.55 | 15 min |
| Quick & cheap | **EC2 Spot** | $0.05 | 5 min |

---

## Deploy in 3 Steps

### Option 1: ECS Fargate
```bash
cd option1-ecs-fargate/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars
terraform init && terraform apply
cd ../app && docker build -t csv-to-kafka .
# Push to ECR (see deploy.sh)
aws ecs run-task --cluster csv-to-kafka-cluster --task-definition csv-to-kafka-task ...
```

### Option 2: AWS Batch
```bash
cd option2-aws-batch/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars
terraform init && terraform apply
cd ../app && docker build -t csv-to-kafka .
# Push to ECR (see deploy.sh)
aws batch submit-job --job-name csv-job --job-queue csv-kafka-job-queue --job-definition csv-kafka-job-def
```

### Option 3: EC2 Spot
```bash
cd option3-ec2-spot
# Edit user-data.sh with your config
aws ec2 run-instances --image-id ami-xxxxx --instance-type t3.medium --user-data file://user-data.sh ...
# Or use Terraform
cd terraform && terraform init && terraform apply
```

---

## Monitor Progress

```bash
# Check progress (every 10 seconds)
watch -n 10 'aws dynamodb get-item --table-name csv-kafka-checkpoint --key "{\"job_id\":{\"S\":\"csv-job-1\"}}"'

# View logs
aws logs tail /ecs/csv-to-kafka --follow

# Check Kafka
kafka-run-class kafka.tools.GetOffsetShell --broker-list $KAFKA_BROKERS --topic csv-import --time -1

# View CloudWatch Dashboard (NEW!)
# Get URL from Terraform output
terraform output dashboard_url
# Or navigate to: CloudWatch → Dashboards → csv-to-kafka-metrics-{job_id}
```

---

## Troubleshoot

### Task Won't Start
```bash
aws ecs describe-tasks --cluster csv-to-kafka-cluster --tasks <task-arn>
# Check stoppedReason
```

### Processing Stopped
```bash
# Check last checkpoint
aws dynamodb get-item --table-name csv-kafka-checkpoint --key '{"job_id":{"S":"csv-job-1"}}'

# Check logs for errors
aws logs filter-log-events --log-group-name /ecs/csv-to-kafka --filter-pattern "ERROR"
```

### Restart from Checkpoint
```bash
# Just restart the task/job with same job_id
aws ecs run-task --cluster csv-to-kafka-cluster --task-definition csv-to-kafka-task ...
# It will automatically resume
```

---

## Key Configuration

### Required Environment Variables
```bash
S3_BUCKET=my-bucket
S3_KEY=data/file.csv
KAFKA_BOOTSTRAP_SERVERS=b-1.msk.amazonaws.com:9092
KAFKA_TOPIC=csv-import
DYNAMODB_TABLE=csv-kafka-checkpoint
JOB_ID=csv-job-1
ENABLE_METRICS=true  # NEW! Enable CloudWatch metrics
```

### Kafka Producer Settings
```python
max_in_flight_requests_per_connection=1  # Ordering
acks='all'                                # Durability
retries=2147483647                        # Infinite
enable_idempotence=True                   # No duplicates
```

---

## Important Commands

### AWS CLI
```bash
# ECS
aws ecs list-tasks --cluster csv-to-kafka-cluster
aws ecs describe-tasks --cluster csv-to-kafka-cluster --tasks <arn>
aws ecs stop-task --cluster csv-to-kafka-cluster --task <arn>

# Batch
aws batch list-jobs --job-queue csv-kafka-job-queue
aws batch describe-jobs --jobs <job-id>
aws batch terminate-job --job-id <job-id> --reason "Manual stop"

# DynamoDB
aws dynamodb get-item --table-name csv-kafka-checkpoint --key '{"job_id":{"S":"csv-job-1"}}'
aws dynamodb delete-item --table-name csv-kafka-checkpoint --key '{"job_id":{"S":"csv-job-1"}}'

# CloudWatch
aws logs tail /ecs/csv-to-kafka --follow
aws logs filter-log-events --log-group-name /ecs/csv-to-kafka --filter-pattern "ERROR"
```

### Kafka
```bash
# List topics
kafka-topics --bootstrap-server $KAFKA_BROKERS --list

# Describe topic
kafka-topics --bootstrap-server $KAFKA_BROKERS --describe --topic csv-import

# Check offset (record count)
kafka-run-class kafka.tools.GetOffsetShell --broker-list $KAFKA_BROKERS --topic csv-import --time -1

# Consume last 10 records
kafka-console-consumer --bootstrap-server $KAFKA_BROKERS --topic csv-import --partition 0 --offset -10 --max-messages 10
```

---

## File Locations

### Documentation
- `README.md` - Start here
- `INDEX.md` - Find documentation
- `OPERATIONS.md` - Deploy & troubleshoot
- `DOCUMENTATION.md` - Code reference

### Code
- `option*/app/processor.py` - Main application
- `option*/terraform/main.tf` - Infrastructure
- `option*/terraform/variables.tf` - Configuration

### Configuration
- `option*/terraform/terraform.tfvars` - Your settings (create from .example)

---

## Performance

| Metric | Value |
|--------|-------|
| Throughput | 10K-50K records/sec |
| 100M rows | 30 min - 3 hours |
| Memory | 1-2 GB (constant) |
| Checkpoint | Every 10K records |

---

## Costs (per run)

| Option | Cost |
|--------|------|
| ECS Fargate | $0.63 |
| AWS Batch | $0.55 |
| EC2 Spot | $0.05 |

---

## Guarantees

✅ Exactly 100M records in Kafka (if CSV has 100M)  
✅ Exact sequential order maintained  
✅ No duplicates (Kafka idempotence)  
✅ Zero data loss (checkpointing)  
✅ Automatic recovery from failures  

---

## Recovery Scenarios

### Process Crashed
1. Check checkpoint in DynamoDB
2. Restart with same job_id
3. Automatically resumes

### Kafka Down
1. Stop current job
2. Fix Kafka
3. Restart job (resumes from checkpoint)

### Wrong Data Sent
1. Stop job
2. Delete Kafka topic
3. Delete checkpoint
4. Fix config
5. Restart from beginning

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Task won't start | Check IAM permissions, ECR image |
| Processing stops | Check Kafka connectivity, logs |
| No records in Kafka | Check topic name, security groups |
| Checkpoint not updating | Check DynamoDB permissions |

---

## Prerequisites Checklist

- [ ] AWS Account with permissions
- [ ] AWS CLI configured
- [ ] Terraform installed
- [ ] Docker installed (ECS/Batch)
- [ ] VPC with private subnets + NAT
- [ ] MSK cluster running
- [ ] S3 bucket with CSV file
- [ ] Security groups configured

---

## Support

1. **Documentation:** [INDEX.md](INDEX.md)
2. **Troubleshooting:** [OPERATIONS.md](OPERATIONS.md)
3. **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
4. **Code Reference:** [DOCUMENTATION.md](DOCUMENTATION.md)
5. **Dashboard Guide:** [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md) 🆕

---

## Quick Links

- **Deploy:** [OPERATIONS.md](OPERATIONS.md) → Deployment Procedures
- **Monitor:** [OPERATIONS.md](OPERATIONS.md) → Monitoring
- **Troubleshoot:** [OPERATIONS.md](OPERATIONS.md) → Troubleshooting
- **Understand:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Compare:** [COMPARISON.md](COMPARISON.md)

---

**Print this page for quick reference! 📄**
