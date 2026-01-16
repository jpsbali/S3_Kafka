# Architecture Documentation

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│                                                                   │
│  ┌──────────┐         ┌─────────────┐         ┌──────────────┐ │
│  │          │ Stream  │             │ Send    │              │ │
│  │  S3 CSV  │────────▶│  Processor  │────────▶│  Kafka/MSK   │ │
│  │  File    │  Read   │  (ECS/Batch │ Records │  Topic       │ │
│  │          │         │   /EC2)     │         │  Partition 0 │ │
│  └──────────┘         └──────┬──────┘         └──────────────┘ │
│                              │                                   │
│                              │ Checkpoint                        │
│                              ▼                                   │
│                       ┌─────────────┐                           │
│                       │  DynamoDB   │                           │
│                       │  Checkpoint │                           │
│                       │  Table      │                           │
│                       └─────────────┘                           │
│                                                                   │
│                       ┌─────────────┐                           │
│                       │ CloudWatch  │                           │
│                       │    Logs     │                           │
│                       └─────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

## Option 1: ECS Fargate Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      ECS Fargate Solution                        │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    VPC (Private Subnet)                   │  │
│  │                                                            │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │           ECS Cluster                              │  │  │
│  │  │                                                     │  │  │
│  │  │  ┌──────────────────────────────────────────────┐ │  │  │
│  │  │  │  Fargate Task                                 │ │  │  │
│  │  │  │                                                │ │  │  │
│  │  │  │  ┌──────────────────────────────────────┐    │ │  │  │
│  │  │  │  │  Container (from ECR)                │    │ │  │  │
│  │  │  │  │                                       │    │ │  │  │
│  │  │  │  │  - processor.py                      │    │ │  │  │
│  │  │  │  │  - CheckpointManager                 │    │ │  │  │
│  │  │  │  │  - CSVToKafkaProcessor               │    │ │  │  │
│  │  │  │  │                                       │    │ │  │  │
│  │  │  │  └───────────────────────────────────────┘    │ │  │  │
│  │  │  │                                                │ │  │  │
│  │  │  │  Task Role: S3, DynamoDB, MSK access          │ │  │  │
│  │  │  └──────────────────────────────────────────────┘ │  │  │
│  │  │                                                     │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  Security Group: Egress to S3, DynamoDB, MSK, CloudWatch │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │     ECR      │  │  CloudWatch  │  │  DynamoDB    │          │
│  │  Repository  │  │    Logs      │  │  Checkpoint  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Components

1. **ECS Cluster**: Logical grouping of tasks
2. **Fargate Task**: Serverless compute for container
3. **Task Definition**: Container configuration (CPU, memory, env vars)
4. **Task Role**: IAM permissions for application
5. **Execution Role**: IAM permissions for ECS service
6. **Security Group**: Network access control
7. **ECR Repository**: Docker image storage
8. **CloudWatch Logs**: Application logs
9. **DynamoDB Table**: Checkpoint storage

### Data Flow

1. User runs ECS task via AWS CLI or Console
2. ECS pulls container image from ECR
3. Fargate launches task in private subnet
4. Container starts, reads environment variables
5. Processor reads checkpoint from DynamoDB
6. Processor streams CSV from S3 line-by-line
7. Each record sent to Kafka partition 0
8. Every 10K records, checkpoint updated in DynamoDB
9. Logs written to CloudWatch
10. On completion, final checkpoint saved
11. Task terminates

## Option 2: AWS Batch Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AWS Batch Solution                           │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Batch Compute Environment                    │  │
│  │              (Spot Instances)                             │  │
│  │                                                            │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  EC2 Spot Instance (Auto-scaled)                   │  │  │
│  │  │                                                     │  │  │
│  │  │  ┌──────────────────────────────────────────────┐ │  │  │
│  │  │  │  ECS Container                                │ │  │  │
│  │  │  │                                                │ │  │  │
│  │  │  │  - processor.py                               │ │  │  │
│  │  │  │  - CheckpointManager                          │ │  │  │
│  │  │  │  - CSVToKafkaProcessor                        │ │  │  │
│  │  │  │                                                │ │  │  │
│  │  │  └────────────────────────────────────────────────┘ │  │  │
│  │  │                                                     │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Batch Job   │  │  Batch Job   │  │     ECR      │          │
│  │  Definition  │─▶│    Queue     │  │  Repository  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  Retry Strategy: 3 attempts with automatic retry                │
│  Spot Interruption: Automatic failover to new instance          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Components

1. **Batch Compute Environment**: Manages EC2 Spot instances
2. **Batch Job Queue**: Queues jobs for execution
3. **Batch Job Definition**: Container configuration
4. **EC2 Spot Instances**: Cost-optimized compute
5. **Job Role**: IAM permissions for application
6. **Service Role**: IAM permissions for Batch service
7. **ECR Repository**: Docker image storage
8. **CloudWatch Logs**: Application logs
9. **DynamoDB Table**: Checkpoint storage

### Data Flow

1. User submits job to Batch queue
2. Batch provisions Spot instance
3. Batch pulls container from ECR
4. Container runs on EC2 instance
5. Processor reads checkpoint from DynamoDB
6. Processor streams CSV from S3
7. Records sent to Kafka
8. Checkpoints saved to DynamoDB
9. On completion or failure, job status updated
10. If Spot interrupted, Batch automatically retries
11. Instance terminated after job completes

### Spot Interruption Handling

```
Job Running ──▶ Spot Interrupted ──▶ Checkpoint Saved
                       │
                       ▼
              Batch Auto-Retry ──▶ New Instance ──▶ Resume from Checkpoint
```

## Option 3: EC2 Spot Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EC2 Spot Solution                             │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    VPC (Private Subnet)                   │  │
│  │                                                            │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │  EC2 Spot Instance (t3.medium)                     │  │  │
│  │  │                                                     │  │  │
│  │  │  ┌──────────────────────────────────────────────┐ │  │  │
│  │  │  │  User Data Script (on launch)                │ │  │  │
│  │  │  │                                               │ │  │  │
│  │  │  │  1. Install Python & dependencies            │ │  │  │
│  │  │  │  2. Create processor.py                      │ │  │  │
│  │  │  │  3. Run processor                            │ │  │  │
│  │  │  │  4. Shutdown instance on completion          │ │  │  │
│  │  │  │                                               │ │  │  │
│  │  │  └───────────────────────────────────────────────┘ │  │  │
│  │  │                                                     │  │  │
│  │  │  Instance Profile: S3, DynamoDB, MSK access         │  │  │
│  │  │                                                     │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                            │  │
│  │  Security Group: Egress to S3, DynamoDB, MSK              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  DynamoDB    │  │  Instance    │                             │
│  │  Checkpoint  │  │    Logs      │                             │
│  └──────────────┘  └──────────────┘                             │
│                                                                   │
│  Self-Terminating: Instance shuts down after completion         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Components

1. **EC2 Spot Instance**: Single instance for processing
2. **Launch Template**: Instance configuration
3. **User Data Script**: Bootstrap script
4. **Instance Profile**: IAM role for instance
5. **Security Group**: Network access control
6. **DynamoDB Table**: Checkpoint storage

### Data Flow

1. User launches Spot instance (via Terraform or CLI)
2. Instance boots with user-data script
3. Script installs Python and dependencies
4. Script creates processor.py inline
5. Script runs processor with environment variables
6. Processor reads checkpoint from DynamoDB
7. Processor streams CSV from S3
8. Records sent to Kafka
9. Checkpoints saved to DynamoDB
10. On completion, instance self-terminates
11. Logs available in `/var/log/csv-processor.log`

## Network Architecture

### VPC Configuration

```
┌─────────────────────────────────────────────────────────────────┐
│                            VPC                                   │
│                                                                   │
│  ┌────────────────────────┐  ┌────────────────────────┐         │
│  │  Public Subnet         │  │  Private Subnet        │         │
│  │                        │  │                        │         │
│  │  ┌──────────────────┐ │  │  ┌──────────────────┐ │         │
│  │  │  NAT Gateway     │ │  │  │  ECS Task /      │ │         │
│  │  │                  │ │  │  │  Batch Job /     │ │         │
│  │  └──────────────────┘ │  │  │  EC2 Instance    │ │         │
│  │                        │  │  │                  │ │         │
│  │  ┌──────────────────┐ │  │  └──────────────────┘ │         │
│  │  │  Internet        │ │  │           │            │         │
│  │  │  Gateway         │ │  │           │            │         │
│  │  └──────────────────┘ │  │           │            │         │
│  │           │            │  │           │            │         │
│  └───────────┼────────────┘  └───────────┼────────────┘         │
│              │                           │                       │
│              │                           │                       │
│              ▼                           ▼                       │
│         Internet                    NAT Gateway                 │
│                                          │                       │
│                                          ▼                       │
│                                     Internet                     │
│                                                                   │
│  Route Tables:                                                   │
│  - Public: 0.0.0.0/0 → Internet Gateway                         │
│  - Private: 0.0.0.0/0 → NAT Gateway                             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Security Groups

**Processor Security Group:**
```
Inbound Rules: None (no incoming connections needed)

Outbound Rules:
- All traffic (0.0.0.0/0) on all ports
  (Required for S3, DynamoDB, MSK, CloudWatch)
```

**MSK Security Group:**
```
Inbound Rules:
- Port 9092 (Kafka) from Processor Security Group
- Port 9094 (TLS) from Processor Security Group

Outbound Rules:
- All traffic
```

## Data Flow Sequence

### Sequential Processing Flow

```
1. Start
   │
   ▼
2. Read Checkpoint from DynamoDB
   │ (Returns: last_line = N)
   ▼
3. Open S3 CSV Stream
   │
   ▼
4. Read CSV Header
   │
   ▼
5. For each row (starting from N+1):
   │
   ├─▶ 6. Read Row
   │   │
   │   ▼
   │   7. Send to Kafka Partition 0
   │   │
   │   ▼
   │   8. Wait for Kafka Confirmation
   │   │
   │   ▼
   │   9. If (row_count % 10000 == 0):
   │   │   │
   │   │   ├─▶ Flush Kafka Producer
   │   │   │
   │   │   └─▶ Update Checkpoint in DynamoDB
   │   │
   │   └─▶ Continue to next row
   │
   ▼
10. All rows processed
    │
    ▼
11. Flush Kafka Producer
    │
    ▼
12. Mark Complete in DynamoDB
    │
    ▼
13. Close Kafka Producer
    │
    ▼
14. Exit (Success)
```

### Error Handling Flow

```
Error Occurs
   │
   ▼
Is it Kafka Error?
   │
   ├─▶ Yes ──▶ Retry (up to 5 times)
   │           │
   │           ├─▶ Success ──▶ Continue
   │           │
   │           └─▶ All retries failed
   │                   │
   │                   ▼
   │               Save Checkpoint
   │                   │
   │                   ▼
   │               Log Error
   │                   │
   │                   ▼
   │               Exit (Failure)
   │
   └─▶ No ──▶ Save Checkpoint
               │
               ▼
           Log Error
               │
               ▼
           Exit (Failure)
```

## Checkpoint Recovery Flow

```
Process Starts
   │
   ▼
Query DynamoDB for job_id
   │
   ├─▶ Checkpoint exists?
   │   │
   │   ├─▶ Yes ──▶ Read last_line
   │   │           │
   │   │           ▼
   │   │       Skip to line (last_line + 1)
   │   │           │
   │   │           ▼
   │   │       Resume processing
   │   │
   │   └─▶ No ──▶ Start from line 1
   │               │
   │               ▼
   │           Process all records
   │
   ▼
Continue normal processing
```

## Kafka Integration

### Producer Configuration

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kafka Producer Settings                       │
│                                                                   │
│  max_in_flight_requests_per_connection = 1                      │
│  ├─▶ Only 1 request at a time                                   │
│  └─▶ Guarantees ordering                                        │
│                                                                   │
│  acks = 'all'                                                    │
│  ├─▶ Wait for all replicas to acknowledge                       │
│  └─▶ Guarantees durability                                      │
│                                                                   │
│  retries = 2147483647                                            │
│  ├─▶ Retry indefinitely on failure                              │
│  └─▶ Prevents data loss                                         │
│                                                                   │
│  enable_idempotence = True                                       │
│  ├─▶ Kafka deduplicates retries                                 │
│  └─▶ Prevents duplicates                                        │
│                                                                   │
│  compression_type = 'gzip'                                       │
│  ├─▶ Compress messages                                          │
│  └─▶ Reduces network usage                                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Message Flow to Kafka

```
Record ──▶ Producer Buffer ──▶ Batch ──▶ Send to Broker
                                            │
                                            ▼
                                    Leader Replica
                                            │
                                            ├─▶ Follower Replica 1
                                            │
                                            └─▶ Follower Replica 2
                                            │
                                            ▼
                                    All Replicas ACK
                                            │
                                            ▼
                                    Confirmation to Producer
                                            │
                                            ▼
                                    Application Continues
```

## Deployment Architecture

### Terraform Workflow

```
1. terraform init
   │
   ▼
2. Download providers (AWS)
   │
   ▼
3. terraform plan
   │
   ▼
4. Show resources to create:
   - DynamoDB table
   - IAM roles & policies
   - Security groups
   - ECS cluster / Batch environment / Launch template
   - ECR repository (ECS/Batch)
   - CloudWatch log groups
   │
   ▼
5. terraform apply
   │
   ▼
6. Create all resources
   │
   ▼
7. Output resource identifiers
   │
   ▼
8. Build Docker image (ECS/Batch)
   │
   ▼
9. Push to ECR (ECS/Batch)
   │
   ▼
10. Ready to run
```

## Monitoring Architecture

### CloudWatch Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                        CloudWatch                                │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Log Groups                             │  │
│  │                                                            │  │
│  │  /ecs/csv-to-kafka          (ECS Fargate logs)           │  │
│  │  /aws/batch/csv-to-kafka    (AWS Batch logs)             │  │
│  │                                                            │  │
│  │  Log Streams:                                             │  │
│  │  - Task/Job ID                                            │  │
│  │  - Timestamp                                              │  │
│  │                                                            │  │
│  │  Log Events:                                              │  │
│  │  - INFO: Progress updates                                 │  │
│  │  - WARNING: Retry attempts                                │  │
│  │  - ERROR: Failures                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Metrics (Optional)                     │  │
│  │                                                            │  │
│  │  - Records processed per minute                           │  │
│  │  - Kafka send latency                                     │  │
│  │  - Error rate                                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Alarms (Optional)                      │  │
│  │                                                            │  │
│  │  - Task/Job failure                                       │  │
│  │  - High error rate                                        │  │
│  │  - Processing stalled                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Cost Architecture

### Cost Breakdown by Option

**Option 1: ECS Fargate**
```
┌─────────────────────────────────────────┐
│ ECS Fargate (2 vCPU, 4GB, 3 hours)     │
│ $0.04048/hour × 3 = $0.12              │
├─────────────────────────────────────────┤
│ DynamoDB (on-demand, ~100 writes)      │
│ $0.01                                   │
├─────────────────────────────────────────┤
│ CloudWatch Logs (1 GB)                  │
│ $0.50                                   │
├─────────────────────────────────────────┤
│ Data Transfer (S3 → ECS, same region)  │
│ $0.00 (free)                            │
├─────────────────────────────────────────┤
│ TOTAL: ~$0.63 per run                   │
└─────────────────────────────────────────┘
```

**Option 2: AWS Batch (Spot)**
```
┌─────────────────────────────────────────┐
│ EC2 Spot (t3.medium, 3 hours, 70% off) │
│ $0.0416/hour × 0.3 × 3 = $0.04         │
├─────────────────────────────────────────┤
│ DynamoDB (on-demand, ~100 writes)      │
│ $0.01                                   │
├─────────────────────────────────────────┤
│ CloudWatch Logs (1 GB)                  │
│ $0.50                                   │
├─────────────────────────────────────────┤
│ TOTAL: ~$0.55 per run                   │
└─────────────────────────────────────────┘
```

**Option 3: EC2 Spot**
```
┌─────────────────────────────────────────┐
│ EC2 Spot (t3.medium, 3 hours, 70% off) │
│ $0.0416/hour × 0.3 × 3 = $0.04         │
├─────────────────────────────────────────┤
│ DynamoDB (on-demand, ~100 writes)      │
│ $0.01                                   │
├─────────────────────────────────────────┤
│ TOTAL: ~$0.05 per run                   │
└─────────────────────────────────────────┘
```

## Scalability Considerations

### Current Design (Sequential)

```
Throughput: 10,000 - 50,000 records/sec
Bottleneck: Single partition, sequential processing
Max Scale: Limited by single instance performance
```

### Future Parallel Design (Not Implemented)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Parallel Processing (Future)                  │
│                                                                   │
│  CSV File ──▶ Split by ranges ──▶ Multiple Processors           │
│                                    │                              │
│                                    ├─▶ Processor 1 → Partition 0 │
│                                    ├─▶ Processor 2 → Partition 1 │
│                                    └─▶ Processor 3 → Partition 2 │
│                                                                   │
│  Trade-off: Faster but loses global ordering                    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

**Document Version:** 1.0.0  
**Last Updated:** January 16, 2026
