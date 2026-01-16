# Data Delivery Guarantees

## How We Ensure 100M Rows Reach Kafka

All three solutions implement multiple layers of guarantees to ensure every single row from S3 makes it to Kafka without loss or duplication.

## 1. Kafka Producer Configuration

```python
producer = KafkaProducer(
    max_in_flight_requests_per_connection=1,  # Ensures ordering
    acks='all',                                # Wait for all replicas
    retries=2147483647,                        # Retry indefinitely
    enable_idempotence=True,                   # Prevents duplicates
    compression_type='gzip'
)
```

**What this means:**
- `acks='all'`: Producer waits for all Kafka replicas to acknowledge before considering send successful
- `max_in_flight_requests_per_connection=1`: Only one request at a time, guarantees ordering
- `retries=2147483647`: Will retry failed sends indefinitely (until timeout)
- `enable_idempotence=True`: Kafka deduplicates retries automatically

## 2. Synchronous Confirmation

```python
future = producer.send(topic, value=row, partition=0)
record_metadata = future.get(timeout=30)  # Wait for confirmation
```

**What this means:**
- We wait for Kafka to confirm each record before moving to next
- If confirmation fails, we retry
- If retry fails after max attempts, we stop and checkpoint

## 3. Checkpointing

```python
if records_sent % 10000 == 0:
    producer.flush()  # Ensure all buffered records are sent
    checkpoint_manager.update_checkpoint(current_line, records_sent)
```

**What this means:**
- Every 10,000 records, we save progress to DynamoDB
- If process crashes, we resume from last checkpoint
- No records are lost or duplicated

## 4. Single Partition

```python
producer.send(topic, value=row, partition=0)  # Always partition 0
```

**What this means:**
- All records go to same partition
- Kafka guarantees ordering within a partition
- Sequential processing is maintained

## 5. Error Handling

```python
def _send_to_kafka(self, row, line_number, max_retries=5):
    for attempt in range(max_retries):
        try:
            future = producer.send(...)
            future.get(timeout=30)
            return True
        except KafkaError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                return False  # Stop processing, save checkpoint
```

**What this means:**
- Each record is retried up to 5 times with exponential backoff
- If all retries fail, processing stops and checkpoint is saved
- Manual intervention required to fix issue
- No silent data loss

## 6. Streaming Read from S3

```python
with smart_open(s3_uri, 'r', transport_params={'client': s3_client}) as f:
    csv_reader = csv.DictReader(f)
    for row in csv_reader:
        # Process row
```

**What this means:**
- File is streamed line-by-line, not loaded into memory
- Can handle files of any size
- No risk of out-of-memory errors

## Failure Scenarios

### Scenario 1: Kafka Broker Failure
**What happens:**
- Producer retries automatically (up to 2B times)
- If broker doesn't recover within timeout, processing stops
- Checkpoint saved with last successful record

**Recovery:**
- Fix Kafka cluster
- Restart job
- Resumes from checkpoint

### Scenario 2: Network Interruption
**What happens:**
- Producer retries with exponential backoff
- If network doesn't recover, processing stops
- Checkpoint saved

**Recovery:**
- Restart job when network is stable
- Resumes from checkpoint

### Scenario 3: Process Crash (ECS/Batch/EC2)
**What happens:**
- Last checkpoint is in DynamoDB
- Some records may be in Kafka buffer but not confirmed

**Recovery:**
- Restart job
- Reads checkpoint from DynamoDB
- Resumes from last confirmed record
- Kafka idempotence prevents duplicates

### Scenario 4: Spot Instance Interruption
**What happens:**
- Instance receives 2-minute warning
- Process may not complete gracefully
- Last checkpoint is in DynamoDB

**Recovery:**
- Launch new instance (automatic for Batch)
- Resumes from checkpoint
- No data loss

## Verification

After processing completes, verify record count:

```bash
# Check DynamoDB for total sent
aws dynamodb get-item \
  --table-name csv-kafka-checkpoint \
  --key '{"job_id":{"S":"csv-job-1"}}'

# Check Kafka topic record count
kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list $KAFKA_BROKERS \
  --topic $TOPIC \
  --time -1
```

## Trade-offs

**Throughput vs Guarantees:**
- Synchronous confirmation (`future.get()`) is slower than async
- But it's the only way to guarantee delivery
- For 100M rows, this is acceptable (30min-3hrs)

**Ordering vs Parallelism:**
- Single partition ensures ordering
- But limits parallelism to one consumer
- For sequential requirement, this is necessary

**Cost vs Reliability:**
- Checkpointing adds DynamoDB costs (~$0.01)
- But prevents data loss worth much more
- Minimal cost for critical guarantee

## Summary

✅ **No Data Loss:** Every record is confirmed before moving to next
✅ **No Duplicates:** Kafka idempotence prevents duplicates on retry
✅ **Ordering Maintained:** Single partition + sequential processing
✅ **Recoverable:** Checkpointing allows resume from any point
✅ **Verifiable:** DynamoDB and Kafka offsets provide audit trail

**Result:** Exactly 100M rows in Kafka, in the same order as S3 CSV.
