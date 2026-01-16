# Code Documentation

## Overview

This document provides detailed documentation for the CSV to Kafka processor codebase across all three implementation options.

## Core Components

### 1. CheckpointManager Class

**Purpose:** Manages progress tracking in DynamoDB for recovery capability

**Location:** All `processor.py` files

#### Methods

##### `__init__(table_name: str, job_id: str)`
Initializes the checkpoint manager.

**Parameters:**
- `table_name`: DynamoDB table name for checkpoints
- `job_id`: Unique identifier for this processing job

**Example:**
```python
checkpoint_mgr = CheckpointManager('csv-kafka-checkpoint', 'csv-job-1')
```

##### `get_last_processed_line() -> int`
Retrieves the last successfully processed line number from DynamoDB.

**Returns:** Line number (0 if no checkpoint exists)

**Error Handling:** Returns 0 on any error (treats as new job)

**Example:**
```python
start_line = checkpoint_mgr.get_last_processed_line()
# Returns: 50000 (if job previously stopped at line 50000)
```

##### `update_checkpoint(line_number: int, total_sent: int)`
Saves current progress to DynamoDB.

**Parameters:**
- `line_number`: Current CSV line number
- `total_sent`: Total records successfully sent to Kafka

**Raises:** `ClientError` if DynamoDB write fails

**Example:**
```python
checkpoint_mgr.update_checkpoint(10000, 10000)
# Saves: {job_id: 'csv-job-1', last_line: 10000, total_sent: 10000, timestamp: 1705420800}
```

##### `mark_complete(total_lines: int)`
Marks the job as completed in DynamoDB.

**Parameters:**
- `total_lines`: Total number of lines processed

**Example:**
```python
checkpoint_mgr.mark_complete(100000000)
# Saves: {job_id: 'csv-job-1', last_line: 100000000, status: 'COMPLETED', ...}
```

---

### 2. CSVToKafkaProcessor Class

**Purpose:** Main processor that orchestrates CSV reading and Kafka writing

**Location:** All `processor.py` files

#### Attributes

- `s3_bucket`: S3 bucket name
- `s3_key`: S3 object key (file path)
- `kafka_topic`: Target Kafka topic
- `checkpoint_manager`: CheckpointManager instance
- `checkpoint_interval`: Records between checkpoints (default: 10000)
- `producer`: KafkaProducer instance
- `s3_client`: Boto3 S3 client

#### Methods

##### `__init__(...)`
Initializes the processor with configuration.

**Parameters:**

- `s3_bucket`: S3 bucket containing CSV
- `s3_key`: Path to CSV file in bucket
- `kafka_bootstrap_servers`: Comma-separated Kafka broker addresses
- `kafka_topic`: Target Kafka topic name
- `checkpoint_manager`: CheckpointManager instance
- `checkpoint_interval`: Records between checkpoints (default: 10000)

**Kafka Producer Configuration:**
```python
KafkaProducer(
    bootstrap_servers=kafka_bootstrap_servers.split(','),
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    max_in_flight_requests_per_connection=1,  # Ensures ordering
    acks='all',                                # Wait for all replicas
    retries=2147483647,                        # Retry indefinitely
    max_block_ms=60000,                        # Wait up to 60s for buffer
    enable_idempotence=True,                   # Prevents duplicates
    compression_type='gzip'                    # Compress messages
)
```

##### `process()`
Main processing loop - reads CSV and sends to Kafka.

**Flow:**
1. Get last checkpoint from DynamoDB
2. Open S3 file as stream
3. Read CSV line by line
4. Skip already-processed lines
5. Send each record to Kafka
6. Checkpoint every N records
7. Mark complete when done

**Error Handling:**
- Stops on send failure
- Saves checkpoint before raising exception
- Closes Kafka producer in finally block

**Example:**
```python
processor = CSVToKafkaProcessor(...)
processor.process()  # Runs until complete or error
```

##### `_send_to_kafka(row: Dict, line_number: int, max_retries: int = 5) -> bool`
Sends a single record to Kafka with retry logic.

**Parameters:**
- `row`: CSV row as dictionary
- `line_number`: Line number in source file
- `max_retries`: Maximum retry attempts (default: 5)

**Returns:** `True` if successful, `False` if all retries failed

**Record Enrichment:**
Adds metadata to each record:
```python
{
    ...original_csv_fields,
    '_source_line': line_number,
    '_source_file': 's3://bucket/key'
}
```

**Retry Logic:**
- Exponential backoff: 2^attempt seconds
- Waits for Kafka confirmation (timeout: 30s)
- Logs warnings on retry
- Returns False after max_retries

**Example:**
```python
success = processor._send_to_kafka({'id': 1, 'name': 'test'}, 1)
# Returns: True (if sent successfully)
```

---

### 3. Main Function

**Purpose:** Entry point that validates config and runs processor

**Location:** All `processor.py` files

#### Flow

1. **Read Environment Variables**
   ```python
   S3_BUCKET
   S3_KEY
   KAFKA_BOOTSTRAP_SERVERS
   KAFKA_TOPIC
   DYNAMODB_TABLE
   JOB_ID (optional, defaults to 'csv-job-1')
   ```

2. **Validate Configuration**
   - Checks all required variables are set
   - Exits with code 1 if any missing

3. **Initialize Components**
   - Create CheckpointManager
   - Create CSVToKafkaProcessor

4. **Run Processing**
   - Call `processor.process()`
   - Exit with code 0 on success
   - Exit with code 1 on failure

**Example:**
```python
if __name__ == '__main__':
    main()
```

---

## Infrastructure Components

### Terraform Resources

#### DynamoDB Table

**Purpose:** Store checkpoint data

**Configuration:**
```hcl
resource "aws_dynamodb_table" "checkpoint" {
  name         = "csv-kafka-checkpoint"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "job_id"
  
  attribute {
    name = "job_id"
    type = "S"
  }
}
```

**Schema:**
- `job_id` (String, Primary Key): Unique job identifier
- `last_line` (Number): Last processed line number
- `total_sent` (Number): Total records sent
- `timestamp` (Number): Unix timestamp
- `status` (String): Job status (optional)

#### IAM Roles

**Task Execution Role** (ECS/Batch):
- Pulls container images from ECR
- Writes logs to CloudWatch

**Task Role** (Application):
- Reads from S3 bucket
- Writes to DynamoDB table
- Connects to MSK cluster

**Permissions:**
```json
{
  "S3": ["s3:GetObject", "s3:ListBucket"],
  "DynamoDB": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
  "Kafka": ["kafka-cluster:*"]
}
```

#### Security Groups

**Egress Rules:**
- Allow all outbound traffic (0.0.0.0/0)
- Required for: S3, DynamoDB, MSK, CloudWatch

**Ingress Rules:**
- None required (processor is client-only)

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `S3_BUCKET` | S3 bucket name | `my-data-bucket` |
| `S3_KEY` | CSV file path | `exports/data.csv` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers | `b-1.msk.com:9092,b-2.msk.com:9092` |
| `KAFKA_TOPIC` | Target topic | `csv-import` |
| `DYNAMODB_TABLE` | Checkpoint table | `csv-kafka-checkpoint` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JOB_ID` | Unique job identifier | `csv-job-1` |

---

## Dependencies

### Python Packages

**boto3** (v1.34.34)
- AWS SDK for Python
- Used for: S3 streaming, DynamoDB operations

**kafka-python** (v2.0.2)
- Pure Python Kafka client
- Used for: Kafka producer

**smart-open** (v6.4.0)
- Library for streaming from cloud storage
- Used for: S3 file streaming without full download

### Installation

```bash
pip install boto3==1.34.34 kafka-python==2.0.2 smart-open[s3]==6.4.0
```

---

## Logging

### Log Levels

- **INFO**: Normal operation (progress updates, completion)
- **WARNING**: Retryable errors (Kafka retry attempts)
- **ERROR**: Fatal errors (max retries exceeded, config missing)
- **DEBUG**: Detailed operation info (each record sent)

### Log Format

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**Example:**
```
2026-01-16 10:30:45 - __main__ - INFO - Starting from line 50000
2026-01-16 10:31:00 - __main__ - INFO - Progress: 10000 records sent (line 60000)
```

### CloudWatch Log Groups

- **ECS Fargate:** `/ecs/csv-to-kafka`
- **AWS Batch:** `/aws/batch/csv-to-kafka`
- **EC2:** `/var/log/csv-processor.log` (on instance)

---

## Error Handling

### Error Types

#### 1. Configuration Errors
**Cause:** Missing environment variables
**Handling:** Exit immediately with code 1
**Recovery:** Fix configuration and restart

#### 2. S3 Errors
**Cause:** File not found, permission denied
**Handling:** Exception raised, checkpoint saved
**Recovery:** Fix S3 issue and restart

#### 3. Kafka Errors
**Cause:** Broker unavailable, timeout, network issue
**Handling:** Retry with exponential backoff (up to 5 times)
**Recovery:** Automatic retry or restart after fixing Kafka

#### 4. DynamoDB Errors
**Cause:** Throttling, permission denied
**Handling:** Exception raised
**Recovery:** Fix DynamoDB issue and restart

### Retry Strategy

**Exponential Backoff:**
```python
for attempt in range(max_retries):
    try:
        # Send to Kafka
        return True
    except KafkaError:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s, 8s, 16s
```

**Kafka Producer Retries:**
- Configured for infinite retries at producer level
- Application-level retries: 5 attempts
- Total: Very high resilience to transient failures

---

## Performance Considerations

### Memory Usage

**Streaming Read:**
- CSV file is NOT loaded into memory
- Reads line-by-line using `smart_open`
- Memory usage: ~1-2 GB regardless of file size

**Kafka Buffering:**
- Producer buffers messages before sending
- Default buffer: 32 MB
- Flushed every 10,000 records

### Throughput

**Factors:**
- Network bandwidth to MSK
- Kafka broker performance
- Record size
- Compression (gzip enabled)

**Expected:**
- 10,000-50,000 records/second
- 100M records: 30 minutes to 3 hours

### Optimization Tips

1. **Increase checkpoint interval** (if recovery time acceptable)
   ```python
   checkpoint_interval=50000  # Instead of 10000
   ```

2. **Tune Kafka producer**
   ```python
   linger_ms=10,      # Wait 10ms to batch
   batch_size=32768   # Larger batches
   ```

3. **Use larger instance** (more CPU/network)
   ```
   task_cpu=4096, task_memory=8192  # For ECS
   ```

---

## Testing

### Unit Tests

Test individual components:

```python
def test_checkpoint_manager():
    mgr = CheckpointManager('test-table', 'test-job')
    mgr.update_checkpoint(100, 100)
    assert mgr.get_last_processed_line() == 100

def test_send_to_kafka():
    processor = CSVToKafkaProcessor(...)
    success = processor._send_to_kafka({'test': 'data'}, 1)
    assert success == True
```

### Integration Tests

Test with small CSV:

```bash
# Create test CSV with 1000 rows
# Run processor
# Verify 1000 records in Kafka
# Verify checkpoint shows 1000
```

### Recovery Tests

Test checkpoint recovery:

```bash
# Process 5000 records
# Kill process
# Restart
# Verify resumes from line 5001
# Verify no duplicates in Kafka
```

---

## Deployment Scripts

### deploy.sh (ECS/Batch)

**Purpose:** Automate infrastructure deployment and image build

**Steps:**
1. Get AWS account ID and region
2. Run `terraform apply`
3. Build Docker image
4. Login to ECR
5. Tag and push image
6. Print run command

**Usage:**
```bash
cd option1-ecs-fargate  # or option2-aws-batch
./deploy.sh
```

### launch-spot.sh (EC2)

**Purpose:** Launch EC2 Spot instance manually

**Steps:**
1. Set configuration variables
2. Run `aws ec2 run-instances` with Spot options
3. Print instance ID and monitoring commands

**Usage:**
```bash
cd option3-ec2-spot
# Edit configuration in script
./launch-spot.sh
```

---

## Monitoring and Debugging

### Check Progress

**DynamoDB:**
```bash
aws dynamodb get-item \
  --table-name csv-kafka-checkpoint \
  --key '{"job_id":{"S":"csv-job-1"}}'
```

**CloudWatch Logs:**
```bash
aws logs tail /ecs/csv-to-kafka --follow
```

### Common Issues

**Issue:** "Missing environment variable"
**Solution:** Check task definition or user-data script

**Issue:** "Kafka timeout"
**Solution:** Check MSK security groups, network connectivity

**Issue:** "S3 access denied"
**Solution:** Check IAM role has s3:GetObject permission

**Issue:** "DynamoDB throttling"
**Solution:** Table is on-demand, should not throttle. Check IAM permissions.

---

## Best Practices

1. **Always test with small CSV first** (1000 rows)
2. **Monitor CloudWatch logs** during first run
3. **Verify checkpoint updates** every 10K records
4. **Check Kafka topic offsets** after completion
5. **Use unique job_id** for each CSV file
6. **Keep Terraform state** in S3 backend (not included)
7. **Tag all resources** for cost tracking
8. **Set up CloudWatch alarms** for failures
9. **Document MSK cluster configuration**
10. **Test recovery** before production use

---

## Troubleshooting Guide

### Processor Won't Start

1. Check environment variables are set
2. Check IAM role permissions
3. Check network connectivity (VPC, subnets, NAT)
4. Check CloudWatch logs for errors

### Processing Stops Mid-Run

1. Check CloudWatch logs for error message
2. Check DynamoDB for last checkpoint
3. Check Kafka broker health
4. Check network connectivity
5. Restart with same job_id (will resume)

### Records Not in Kafka

1. Verify topic name is correct
2. Check Kafka topic exists
3. Check partition 0 exists
4. Verify MSK security groups allow traffic
5. Check CloudWatch logs for send confirmations

### Checkpoint Not Updating

1. Check DynamoDB table exists
2. Check IAM permissions for DynamoDB
3. Check CloudWatch logs for DynamoDB errors
4. Verify table name matches environment variable

---

## Code Examples

### Custom Checkpoint Interval

```python
processor = CSVToKafkaProcessor(
    s3_bucket=s3_bucket,
    s3_key=s3_key,
    kafka_bootstrap_servers=kafka_servers,
    kafka_topic=kafka_topic,
    checkpoint_manager=checkpoint_mgr,
    checkpoint_interval=50000  # Checkpoint every 50K records
)
```

### Multiple Jobs

```python
# Job 1
checkpoint_mgr1 = CheckpointManager('csv-kafka-checkpoint', 'file1-job')
processor1 = CSVToKafkaProcessor(..., checkpoint_manager=checkpoint_mgr1)

# Job 2
checkpoint_mgr2 = CheckpointManager('csv-kafka-checkpoint', 'file2-job')
processor2 = CSVToKafkaProcessor(..., checkpoint_manager=checkpoint_mgr2)
```

### Custom Record Transformation

Modify `_send_to_kafka` method:

```python
def _send_to_kafka(self, row: Dict, line_number: int) -> bool:
    # Custom transformation
    enriched_row = {
        'id': row['id'],
        'name': row['name'].upper(),  # Transform
        'timestamp': int(time.time()),
        '_source_line': line_number
    }
    
    future = self.producer.send(self.kafka_topic, value=enriched_row)
    future.get(timeout=30)
    return True
```

---

## Security Considerations

1. **IAM Roles:** Use least privilege principle
2. **Secrets:** Store Kafka credentials in Secrets Manager (if using auth)
3. **Encryption:** Enable encryption in transit (TLS) for MSK
4. **VPC:** Run in private subnets, no public IPs
5. **Logging:** Don't log sensitive data from CSV
6. **Access:** Restrict S3 bucket access to specific roles

---

## Maintenance

### Regular Tasks

- Review CloudWatch logs for errors
- Monitor DynamoDB for stuck jobs
- Check Kafka topic lag
- Update Python dependencies
- Review AWS costs

### Updates

**Python Dependencies:**
```bash
pip install --upgrade boto3 kafka-python smart-open
# Update requirements.txt
# Rebuild Docker image
```

**Terraform:**
```bash
terraform plan  # Review changes
terraform apply # Apply updates
```

---

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review this documentation
3. Check DynamoDB checkpoint table
4. Verify Kafka topic state
5. Review Terraform state

---

## Appendix

### Kafka Producer Configuration Reference

| Parameter | Value | Reason |
|-----------|-------|--------|
| `max_in_flight_requests_per_connection` | 1 | Ensures ordering |
| `acks` | all | Wait for all replicas |
| `retries` | 2147483647 | Retry indefinitely |
| `enable_idempotence` | True | Prevents duplicates |
| `compression_type` | gzip | Reduce network usage |
| `max_block_ms` | 60000 | Wait for buffer space |

### DynamoDB Item Structure

```json
{
  "job_id": "csv-job-1",
  "last_line": 50000,
  "total_sent": 50000,
  "timestamp": 1705420800,
  "status": "IN_PROGRESS"
}
```

### S3 Streaming Details

Uses `smart_open` library:
- Opens S3 object as file-like object
- Reads in chunks (default: 50 KB)
- No full download required
- Supports files of any size

---

**Document Version:** 1.0.0  
**Last Updated:** January 16, 2026
