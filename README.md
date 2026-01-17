# CSV to Kafka Sequential Processor - AWS Solutions
# Spec coded using Kiro

Three production-ready solutions for processing 100M rows from S3 to Kafka with guaranteed delivery and ordering.

## Solutions Overview

### Option 1: ECS Fargate (Recommended for Production)
**Best for:** Production workloads, managed infrastructure, automatic scaling

**Pros:**
- Fully serverless (no EC2 management)
- Automatic retries and health checks
- CloudWatch integration
- Easy to monitor and debug

**Cons:**
- Slightly higher cost than Spot instances
- Requires container registry (ECR)

**Cost:** ~$0.50-2.00 per run

### Option 2: AWS Batch with Spot Instances
**Best for:** Cost optimization, batch processing workloads

**Pros:**
- Up to 90% cost savings with Spot
- Automatic retry on Spot interruption
- Managed job scheduling
- Built-in retry logic

**Cons:**
- Requires container setup
- Slightly more complex than EC2

**Cost:** ~$0.10-0.50 per run

### Option 3: EC2 Spot Instance
**Best for:** Simplicity, one-off jobs, maximum cost savings

**Pros:**
- Simplest setup (just user-data script)
- Lowest cost
- No container required
- Self-terminating

**Cons:**
- Manual instance management
- Less monitoring than ECS/Batch

**Cost:** ~$0.01-0.05 per run

## Key Features (All Solutions)

✅ **Guaranteed Delivery:** Every record is confirmed before moving to next
✅ **Sequential Processing:** Maintains exact order from CSV
✅ **Checkpointing:** Resume from last processed row on failure
✅ **Error Handling:** Automatic retries with exponential backoff
✅ **Idempotence:** No duplicate records on retry
✅ **Monitoring:** CloudWatch logs and DynamoDB progress tracking
✅ **Metrics Dashboard:** Real-time throughput and progress visualization 🆕
✅ **Comprehensive Testing:** 70% test coverage with 47 tests 🆕

## Quick Start

Choose your solution and follow the README in that directory:

```bash
cd option1-ecs-fargate/    # For ECS Fargate
cd option2-aws-batch/      # For AWS Batch
cd option3-ec2-spot/       # For EC2 Spot
```

Each directory contains:
- Complete Terraform infrastructure code
- Application code with error handling
- Deployment scripts
- Configuration examples

## Architecture

All solutions use:
- **S3:** Source CSV file (streaming read, no full download)
- **Amazon MSK:** Kafka cluster (single partition for ordering)
- **DynamoDB:** Checkpoint table (tracks progress)
- **CloudWatch:** Logging and monitoring

## Recovery Process

If processing fails at any point:

1. Check DynamoDB table for last processed line
2. Restart the job (ECS task, Batch job, or EC2 instance)
3. Processor automatically resumes from checkpoint
4. No data loss or duplicates

## Kafka Configuration

All solutions use these settings for guaranteed delivery:
- `acks='all'` - Wait for all replicas
- `max_in_flight_requests_per_connection=1` - Ensures ordering
- `enable_idempotence=True` - Prevents duplicates
- `partition=0` - Single partition for sequential order

## Monitoring Progress

Check DynamoDB table:
```bash
aws dynamodb get-item \
  --table-name csv-kafka-checkpoint \
  --key '{"job_id":{"S":"csv-job-1"}}'
```

Check CloudWatch Logs:
```bash
aws logs tail /ecs/csv-to-kafka --follow  # For ECS
aws logs tail /aws/batch/csv-to-kafka --follow  # For Batch
```

## Performance

Expected throughput: 10,000-50,000 records/second
- 100M rows: 30 minutes to 3 hours
- Depends on: Network speed, Kafka cluster size, record size

## Prerequisites

All solutions require:
- AWS Account with appropriate permissions
- Amazon MSK cluster (or Kafka cluster)
- S3 bucket with CSV file
- VPC with private subnets and NAT gateway
- Terraform (for infrastructure deployment)

## Documentation

This project includes comprehensive documentation (15+ files, 7,000+ lines):

### Quick Start
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** ⭐ - One-page cheat sheet with commands
- **[INDEX.md](INDEX.md)** - Documentation navigation guide
- **[DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)** 🆕 - Metrics dashboard usage guide

### Project Information
- **[PROJECT_SPEC.md](PROJECT_SPEC.md)** - Complete project specification
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Executive summary and recreation guide
- **[COMPLETION_SUMMARY.md](COMPLETION_SUMMARY.md)** - What was delivered

### Technical Documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture with diagrams
- **[DOCUMENTATION.md](DOCUMENTATION.md)** - Code documentation and API reference
- **[OPERATIONS.md](OPERATIONS.md)** - Deployment and operations guide
- **[GUARANTEES.md](GUARANTEES.md)** - Data delivery guarantees explained

### Testing Documentation 🆕
- **[TESTING_PLAN.md](tests/TESTING_PLAN.md)** - Complete testing strategy
- **[TESTING_COMPLETION_SUMMARY.md](TESTING_COMPLETION_SUMMARY.md)** - Test results and coverage
- **[tests/README.md](tests/README.md)** - Testing guide and setup instructions

### Enhancement Documentation 🆕
- **[METRICS_ENHANCEMENT_SUMMARY.md](METRICS_ENHANCEMENT_SUMMARY.md)** - Metrics implementation details
- **[ENHANCEMENT_PLAN_METRICS_DASHBOARD.md](ENHANCEMENT_PLAN_METRICS_DASHBOARD.md)** - Metrics enhancement plan

### Reference
- **[COMPARISON.md](COMPARISON.md)** - Solution comparison matrix
- **[FILE_MANIFEST.md](FILE_MANIFEST.md)** - Complete file listing

Each solution directory also contains specific README files with detailed instructions.

## Support

For help, refer to:
1. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick commands and troubleshooting
2. **[INDEX.md](INDEX.md)** - Find the right documentation
3. **[OPERATIONS.md](OPERATIONS.md)** - Complete troubleshooting guide
4. Solution-specific README files
