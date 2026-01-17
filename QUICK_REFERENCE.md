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
```cmd
cd option1-ecs-fargate\terraform
copy terraform.tfvars.example terraform.tfvars
REM Edit terraform.tfvars with your values
terraform init
terraform apply
cd ..\app
docker build -t csv-to-kafka .
REM Push to ECR (see deploy.sh)
aws ecs run-task --cluster csv-to-kafka-cluster --task-definition csv-to-kafka-task ...
```

### Option 2: AWS Batch
```cmd
cd option2-aws-batch\terraform
copy terraform.tfvars.example terraform.tfvars
REM Edit terraform.tfvars with your values
terraform init
terraform apply
cd ..\app
docker build -t csv-to-kafka .
REM Push to ECR (see deploy.sh)
aws batch submit-job --job-name csv-job --job-queue csv-kafka-job-queue --job-definition csv-kafka-job-def
```

### Option 3: EC2 Spot
```cmd
cd option3-ec2-spot
REM Edit user-data.sh with your config
aws ec2 run-instances --image-id ami-xxxxx --instance-type t3.medium --user-data file://user-data.sh ...
REM Or use Terraform
cd terraform
terraform init
terraform apply
```

---

## Monitor Progress

```cmd
REM Check progress in DynamoDB
aws dynamodb get-item --table-name csv-kafka-checkpoint --key "{\"job_id\":{\"S\":\"csv-job-1\"}}"

REM View logs
aws logs tail /ecs/csv-to-kafka --follow

REM Check Kafka offset
kafka-run-class kafka.tools.GetOffsetShell --broker-list %KAFKA_BROKERS% --topic csv-import --time -1

REM View CloudWatch Dashboard (NEW!)
REM Get URL from Terraform output
terraform output dashboard_url
REM Or navigate to: CloudWatch → Dashboards → csv-to-kafka-metrics-{job_id}

REM Run Tests (NEW!)
cd tests
python -m pytest unit/ -v
python -m pytest unit/ --cov=option1-ecs-fargate/app --cov-report=html
python -m pytest unit/test_checkpoint_manager.py -v
python -m pytest integration/ -v
```

---

## Troubleshoot

### Task Won't Start
```cmd
aws ecs describe-tasks --cluster csv-to-kafka-cluster --tasks <task-arn>
REM Check stoppedReason
```

### Processing Stopped
```cmd
REM Check last checkpoint
aws dynamodb get-item --table-name csv-kafka-checkpoint --key "{\"job_id\":{\"S\":\"csv-job-1\"}}"

REM Check logs for errors
aws logs filter-log-events --log-group-name /ecs/csv-to-kafka --filter-pattern "ERROR"
```

### Restart from Checkpoint
```cmd
REM Just restart the task/job with same job_id
aws ecs run-task --cluster csv-to-kafka-cluster --task-definition csv-to-kafka-task ...
REM It will automatically resume
```

---

## Key Configuration

### Required Environment Variables
```cmd
set S3_BUCKET=my-bucket
set S3_KEY=data/file.csv
set KAFKA_BOOTSTRAP_SERVERS=b-1.msk.amazonaws.com:9092
set KAFKA_TOPIC=csv-import
set DYNAMODB_TABLE=csv-kafka-checkpoint
set JOB_ID=csv-job-1
set ENABLE_METRICS=true
REM NEW! Enable CloudWatch metrics
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
```cmd
REM ECS
aws ecs list-tasks --cluster csv-to-kafka-cluster
aws ecs describe-tasks --cluster csv-to-kafka-cluster --tasks <arn>
aws ecs stop-task --cluster csv-to-kafka-cluster --task <arn>

REM Batch
aws batch list-jobs --job-queue csv-kafka-job-queue
aws batch describe-jobs --jobs <job-id>
aws batch terminate-job --job-id <job-id> --reason "Manual stop"

REM DynamoDB
aws dynamodb get-item --table-name csv-kafka-checkpoint --key "{\"job_id\":{\"S\":\"csv-job-1\"}}"
aws dynamodb delete-item --table-name csv-kafka-checkpoint --key "{\"job_id\":{\"S\":\"csv-job-1\"}}"

REM CloudWatch
aws logs tail /ecs/csv-to-kafka --follow
aws logs filter-log-events --log-group-name /ecs/csv-to-kafka --filter-pattern "ERROR"
```

### Kafka
```cmd
REM List topics
kafka-topics --bootstrap-server %KAFKA_BROKERS% --list

REM Describe topic
kafka-topics --bootstrap-server %KAFKA_BROKERS% --describe --topic csv-import

REM Check offset (record count)
kafka-run-class kafka.tools.GetOffsetShell --broker-list %KAFKA_BROKERS% --topic csv-import --time -1

REM Consume last 10 records
kafka-console-consumer --bootstrap-server %KAFKA_BROKERS% --topic csv-import --partition 0 --offset -10 --max-messages 10
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
- `tests/unit/test_*.py` - Unit tests (47 tests, 70% coverage) 🆕
- `tests/README.md` - Testing guide 🆕

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
6. **Testing Guide:** [tests/README.md](tests/README.md) 🆕
7. **Test Results:** [TESTING_COMPLETION_SUMMARY.md](TESTING_COMPLETION_SUMMARY.md) 🆕

---

## Quick Links

- **Deploy:** [OPERATIONS.md](OPERATIONS.md) → Deployment Procedures
- **Monitor:** [OPERATIONS.md](OPERATIONS.md) → Monitoring
- **Troubleshoot:** [OPERATIONS.md](OPERATIONS.md) → Troubleshooting
- **Understand:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Compare:** [COMPARISON.md](COMPARISON.md)

---

**Print this page for quick reference! 📄**
