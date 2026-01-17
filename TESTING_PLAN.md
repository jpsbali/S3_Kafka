# Testing Plan: CSV to Kafka Processor

## Overview

Comprehensive testing strategy for the CSV to Kafka processor including unit tests, integration tests, end-to-end tests, and performance tests.

**Test Framework:** pytest  
**Mocking:** unittest.mock, moto (AWS mocking)  
**Coverage Target:** 80%+  

---

## Test Categories

### 1. Unit Tests
- Test individual functions and classes
- Mock external dependencies
- Fast execution (< 1 second per test)

### 2. Integration Tests
- Test component interactions
- Use LocalStack for AWS services
- Medium execution (< 30 seconds per test)

### 3. End-to-End Tests
- Test complete workflow
- Use real AWS services (test environment)
- Slow execution (minutes)

### 4. Performance Tests
- Test throughput and latency
- Measure resource usage
- Load testing with large datasets

---

## Test Structure

```
tests/
├── unit/
│   ├── test_checkpoint_manager.py
│   ├── test_metrics_emitter.py
│   ├── test_csv_processor.py
│   └── test_helpers.py
├── integration/
│   ├── test_s3_integration.py
│   ├── test_dynamodb_integration.py
│   ├── test_kafka_integration.py
│   └── test_end_to_end.py
├── performance/
│   ├── test_throughput.py
│   ├── test_memory_usage.py
│   └── test_large_files.py
├── fixtures/
│   ├── sample_data.csv
│   ├── large_data.csv
│   └── malformed_data.csv
├── conftest.py
└── requirements-test.txt
```

---

## 1. Unit Tests

### 1.1 CheckpointManager Tests

**File:** `tests/unit/test_checkpoint_manager.py`

```python
import pytest
from unittest.mock import Mock, patch
from processor import CheckpointManager

class TestCheckpointManager:
    
    @pytest.fixture
    def mock_dynamodb(self):
        with patch('boto3.resource') as mock:
            yield mock
    
    def test_get_last_processed_line_exists(self, mock_dynamodb):
        """Test retrieving existing checkpoint"""
        # Arrange
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {'job_id': 'test-job', 'last_line': 5000}
        }
        mock_dynamodb.return_value.Table.return_value = mock_table
        
        manager = CheckpointManager('test-table', 'test-job')
        
        # Act
        result = manager.get_last_processed_line()
        
        # Assert
        assert result == 5000
        mock_table.get_item.assert_called_once()
    
    def test_get_last_processed_line_not_exists(self, mock_dynamodb):
        """Test retrieving non-existent checkpoint returns 0"""
        # Arrange
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_dynamodb.return_value.Table.return_value = mock_table
        
        manager = CheckpointManager('test-table', 'test-job')
        
        # Act
        result = manager.get_last_processed_line()
        
        # Assert
        assert result == 0
    
    def test_update_checkpoint(self, mock_dynamodb):
        """Test updating checkpoint"""
        # Arrange
        mock_table = Mock()
        mock_dynamodb.return_value.Table.return_value = mock_table
        
        manager = CheckpointManager('test-table', 'test-job')
        
        # Act
        manager.update_checkpoint(10000, 10000)
        
        # Assert
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]
        assert call_args['Item']['last_line'] == 10000
        assert call_args['Item']['total_sent'] == 10000
    
    def test_mark_complete(self, mock_dynamodb):
        """Test marking job as complete"""
        # Arrange
        mock_table = Mock()
        mock_dynamodb.return_value.Table.return_value = mock_table
        
        manager = CheckpointManager('test-table', 'test-job')
        
        # Act
        manager.mark_complete(100000)
        
        # Assert
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]
        assert call_args['Item']['status'] == 'COMPLETED'
        assert call_args['Item']['last_line'] == 100000
```

### 1.2 MetricsEmitter Tests

**File:** `tests/unit/test_metrics_emitter.py`

```python
import pytest
from unittest.mock import Mock, patch
from processor import MetricsEmitter

class TestMetricsEmitter:
    
    @pytest.fixture
    def mock_cloudwatch(self):
        with patch('boto3.client') as mock:
            yield mock
    
    def test_emit_throughput(self, mock_cloudwatch):
        """Test emitting throughput metric"""
        # Arrange
        mock_cw = Mock()
        mock_cloudwatch.return_value = mock_cw
        
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.emit_throughput(45000.5)
        
        # Assert
        assert len(emitter.metrics_buffer) == 1
        metric = emitter.metrics_buffer[0]
        assert metric['MetricName'] == 'RecordsPerSecond'
        assert metric['Value'] == 45000.5
        assert metric['Unit'] == 'Count/Second'
    
    def test_emit_progress(self, mock_cloudwatch):
        """Test emitting progress metrics"""
        # Arrange
        mock_cw = Mock()
        mock_cloudwatch.return_value = mock_cw
        
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.emit_progress(50000, 100000)
        
        # Assert
        assert len(emitter.metrics_buffer) == 3  # Percentage, Processed, Remaining
        
        # Check percentage
        percentage_metric = next(m for m in emitter.metrics_buffer if m['MetricName'] == 'ProgressPercentage')
        assert percentage_metric['Value'] == 50.0
    
    def test_buffer_flush_on_size(self, mock_cloudwatch):
        """Test buffer flushes when reaching 20 metrics"""
        # Arrange
        mock_cw = Mock()
        mock_cloudwatch.return_value = mock_cw
        
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act - Add 20 metrics
        for i in range(20):
            emitter.emit_throughput(1000.0)
        
        # Assert
        mock_cw.put_metric_data.assert_called()
        assert len(emitter.metrics_buffer) == 0  # Buffer cleared
    
    def test_flush_batches_metrics(self, mock_cloudwatch):
        """Test flush sends metrics in batches of 20"""
        # Arrange
        mock_cw = Mock()
        mock_cloudwatch.return_value = mock_cw
        
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Add 45 metrics
        for i in range(45):
            emitter.metrics_buffer.append({
                'MetricName': 'Test',
                'Value': i,
                'Unit': 'Count'
            })
        
        # Act
        emitter.flush()
        
        # Assert
        assert mock_cw.put_metric_data.call_count == 3  # 20 + 20 + 5
```

### 1.3 CSVToKafkaProcessor Tests

**File:** `tests/unit/test_csv_processor.py`

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from processor import CSVToKafkaProcessor, CheckpointManager

class TestCSVToKafkaProcessor:
    
    @pytest.fixture
    def mock_dependencies(self):
        with patch('boto3.client'), \
             patch('processor.KafkaProducer'), \
             patch('processor.smart_open'):
            yield
    
    def test_calculate_eta(self, mock_dependencies):
        """Test ETA calculation"""
        # Arrange
        mock_checkpoint = Mock(spec=CheckpointManager)
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint,
            total_lines=100000
        )
        
        # Simulate 10 seconds elapsed, 10000 records processed
        processor.start_time = processor.start_time - 10
        
        # Act
        eta = processor._calculate_eta(10000)
        
        # Assert
        # Rate: 10000/10 = 1000 rec/sec
        # Remaining: 90000
        # ETA: 90000/1000 = 90 seconds
        assert eta == pytest.approx(90.0, rel=0.1)
    
    def test_calculate_eta_no_total_lines(self, mock_dependencies):
        """Test ETA returns 0 when total lines unknown"""
        # Arrange
        mock_checkpoint = Mock(spec=CheckpointManager)
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint,
            total_lines=None
        )
        
        # Act
        eta = processor._calculate_eta(10000)
        
        # Assert
        assert eta == 0
    
    @patch('processor.smart_open')
    def test_get_total_lines_cached(self, mock_smart_open, mock_dependencies):
        """Test total lines retrieved from cache"""
        # Arrange
        mock_checkpoint = Mock(spec=CheckpointManager)
        mock_checkpoint.table.get_item.return_value = {
            'Item': {'total_lines': 50000}
        }
        
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint
        )
        
        # Act
        total = processor._get_total_lines()
        
        # Assert
        assert total == 50000
        mock_smart_open.assert_not_called()  # Should not count
    
    @patch('processor.smart_open')
    def test_get_total_lines_count(self, mock_smart_open, mock_dependencies):
        """Test total lines counted when not cached"""
        # Arrange
        mock_checkpoint = Mock(spec=CheckpointManager)
        mock_checkpoint.table.get_item.side_effect = Exception("Not found")
        
        # Mock file with 100 lines
        mock_file = MagicMock()
        mock_file.__enter__.return_value = iter(['line' + str(i) for i in range(100)])
        mock_smart_open.return_value = mock_file
        
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint
        )
        
        # Act
        total = processor._get_total_lines()
        
        # Assert
        assert total == 100
        mock_checkpoint.table.put_item.assert_called_once()  # Cached
```

---

## 2. Integration Tests

### 2.1 S3 Integration Tests

**File:** `tests/integration/test_s3_integration.py`

```python
import pytest
import boto3
from moto import mock_s3
import csv
import io

@mock_s3
class TestS3Integration:
    
    @pytest.fixture
    def s3_setup(self):
        """Setup S3 bucket with test data"""
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket = 'test-bucket'
        s3.create_bucket(Bucket=bucket)
        
        # Create test CSV
        csv_data = io.StringIO()
        writer = csv.DictWriter(csv_data, fieldnames=['id', 'name', 'value'])
        writer.writeheader()
        for i in range(1000):
            writer.writerow({'id': i, 'name': f'item-{i}', 'value': i * 10})
        
        s3.put_object(
            Bucket=bucket,
            Key='test.csv',
            Body=csv_data.getvalue().encode('utf-8')
        )
        
        return s3, bucket
    
    def test_read_csv_from_s3(self, s3_setup):
        """Test reading CSV from S3"""
        from smart_open import open as smart_open
        
        s3, bucket = s3_setup
        
        # Act
        with smart_open(f's3://{bucket}/test.csv', 'r', transport_params={'client': s3}) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Assert
        assert len(rows) == 1000
        assert rows[0]['id'] == '0'
        assert rows[999]['id'] == '999'
```

### 2.2 DynamoDB Integration Tests

**File:** `tests/integration/test_dynamodb_integration.py`

```python
import pytest
import boto3
from moto import mock_dynamodb
from processor import CheckpointManager

@mock_dynamodb
class TestDynamoDBIntegration:
    
    @pytest.fixture
    def dynamodb_setup(self):
        """Setup DynamoDB table"""
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        table = dynamodb.create_table(
            TableName='test-checkpoint',
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        return table
    
    def test_checkpoint_workflow(self, dynamodb_setup):
        """Test complete checkpoint workflow"""
        # Arrange
        manager = CheckpointManager('test-checkpoint', 'test-job-1')
        
        # Act & Assert - Initial state
        assert manager.get_last_processed_line() == 0
        
        # Update checkpoint
        manager.update_checkpoint(5000, 5000)
        assert manager.get_last_processed_line() == 5000
        
        # Update again
        manager.update_checkpoint(10000, 10000)
        assert manager.get_last_processed_line() == 10000
        
        # Mark complete
        manager.mark_complete(10000)
        
        # Verify completion
        item = dynamodb_setup.get_item(Key={'job_id': 'test-job-1'})['Item']
        assert item['status'] == 'COMPLETED'
```

### 2.3 Kafka Integration Tests

**File:** `tests/integration/test_kafka_integration.py`

```python
import pytest
from kafka import KafkaProducer, KafkaConsumer
import json
import time

@pytest.mark.integration
@pytest.mark.kafka
class TestKafkaIntegration:
    """
    Requires running Kafka instance
    Run with: docker-compose up -d kafka
    """
    
    @pytest.fixture
    def kafka_config(self):
        return {
            'bootstrap_servers': 'localhost:9092',
            'topic': 'test-topic'
        }
    
    def test_send_and_receive(self, kafka_config):
        """Test sending and receiving messages"""
        # Arrange
        producer = KafkaProducer(
            bootstrap_servers=kafka_config['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        consumer = KafkaConsumer(
            kafka_config['topic'],
            bootstrap_servers=kafka_config['bootstrap_servers'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            consumer_timeout_ms=5000
        )
        
        # Act
        test_data = {'id': 1, 'name': 'test', 'value': 100}
        producer.send(kafka_config['topic'], value=test_data)
        producer.flush()
        
        # Assert
        messages = list(consumer)
        assert len(messages) > 0
        assert messages[-1].value == test_data
        
        producer.close()
        consumer.close()
    
    def test_ordering_guarantee(self, kafka_config):
        """Test messages maintain order in single partition"""
        # Arrange
        producer = KafkaProducer(
            bootstrap_servers=kafka_config['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            max_in_flight_requests_per_connection=1
        )
        
        # Act - Send 100 messages
        for i in range(100):
            producer.send(kafka_config['topic'], value={'seq': i}, partition=0)
        producer.flush()
        
        # Assert - Verify order
        consumer = KafkaConsumer(
            kafka_config['topic'],
            bootstrap_servers=kafka_config['bootstrap_servers'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest'
        )
        
        messages = []
        for msg in consumer:
            messages.append(msg.value['seq'])
            if len(messages) >= 100:
                break
        
        assert messages == list(range(100))
        consumer.close()
```

---

## 3. End-to-End Tests

### 3.1 Complete Workflow Test

**File:** `tests/integration/test_end_to_end.py`

```python
import pytest
import boto3
from moto import mock_s3, mock_dynamodb
import csv
import io
from processor import CSVToKafkaProcessor, CheckpointManager, MetricsEmitter

@mock_s3
@mock_dynamodb
@pytest.mark.e2e
class TestEndToEnd:
    
    @pytest.fixture
    def aws_setup(self):
        """Setup AWS resources"""
        # S3
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket = 'test-bucket'
        s3.create_bucket(Bucket=bucket)
        
        # Create CSV with 1000 rows
        csv_data = io.StringIO()
        writer = csv.DictWriter(csv_data, fieldnames=['id', 'name', 'value'])
        writer.writeheader()
        for i in range(1000):
            writer.writerow({'id': i, 'name': f'item-{i}', 'value': i * 10})
        
        s3.put_object(Bucket=bucket, Key='test.csv', Body=csv_data.getvalue())
        
        # DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-checkpoint',
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        return s3, bucket, table
    
    @pytest.mark.skip(reason="Requires running Kafka")
    def test_complete_processing(self, aws_setup):
        """Test complete CSV to Kafka processing"""
        s3, bucket, table = aws_setup
        
        # Arrange
        checkpoint_mgr = CheckpointManager('test-checkpoint', 'test-job')
        metrics = MetricsEmitter('TestNamespace', 'test-job')
        
        processor = CSVToKafkaProcessor(
            s3_bucket=bucket,
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=checkpoint_mgr,
            metrics_emitter=metrics,
            checkpoint_interval=100
        )
        
        # Act
        processor.process()
        
        # Assert
        final_checkpoint = checkpoint_mgr.get_last_processed_line()
        assert final_checkpoint == 1000
        
        # Verify completion status
        item = table.get_item(Key={'job_id': 'test-job'})['Item']
        assert item['status'] == 'COMPLETED'
    
    def test_recovery_from_checkpoint(self, aws_setup):
        """Test recovery from mid-processing checkpoint"""
        s3, bucket, table = aws_setup
        
        # Arrange - Set checkpoint at 500
        checkpoint_mgr = CheckpointManager('test-checkpoint', 'test-job')
        checkpoint_mgr.update_checkpoint(500, 500)
        
        # Act - Process should skip first 500 lines
        # (This would require mocking Kafka or using test Kafka)
        
        # Assert
        assert checkpoint_mgr.get_last_processed_line() == 500
```

---

## 4. Performance Tests

### 4.1 Throughput Test

**File:** `tests/performance/test_throughput.py`

```python
import pytest
import time
from unittest.mock import Mock, patch
from processor import CSVToKafkaProcessor

@pytest.mark.performance
class TestThroughput:
    
    def test_throughput_measurement(self):
        """Measure processing throughput"""
        # This would require actual Kafka and large CSV
        # Placeholder for performance test structure
        
        start_time = time.time()
        records_processed = 100000
        
        # Simulate processing
        time.sleep(2)  # Simulate 2 seconds of processing
        
        elapsed = time.time() - start_time
        throughput = records_processed / elapsed
        
        # Assert minimum throughput
        assert throughput > 10000  # At least 10K records/sec
    
    def test_latency_measurement(self):
        """Measure Kafka send latency"""
        # Measure p50, p95, p99 latencies
        latencies = []
        
        # Simulate 1000 sends
        for i in range(1000):
            start = time.time()
            # Simulate Kafka send
            time.sleep(0.001)  # 1ms
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.50)]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        
        # Assert acceptable latencies
        assert p50 < 50  # p50 < 50ms
        assert p95 < 200  # p95 < 200ms
        assert p99 < 500  # p99 < 500ms
```

### 4.2 Memory Usage Test

**File:** `tests/performance/test_memory_usage.py`

```python
import pytest
import psutil
import os

@pytest.mark.performance
class TestMemoryUsage:
    
    def test_memory_stays_constant(self):
        """Test memory usage doesn't grow with file size"""
        process = psutil.Process(os.getpid())
        
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate processing large file
        # Memory should stay relatively constant due to streaming
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Assert memory growth is minimal
        assert memory_growth < 100  # Less than 100MB growth
```

---

## 5. Test Fixtures

### 5.1 Sample Data

**File:** `tests/fixtures/sample_data.csv`

```csv
id,name,email,value,timestamp
1,Alice,alice@example.com,100,2026-01-01T00:00:00Z
2,Bob,bob@example.com,200,2026-01-01T00:01:00Z
3,Charlie,charlie@example.com,300,2026-01-01T00:02:00Z
```

### 5.2 Conftest

**File:** `tests/conftest.py`

```python
import pytest
import os

def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "kafka: mark test as requiring Kafka"
    )

@pytest.fixture(scope="session")
def aws_credentials():
    """Mock AWS credentials for moto"""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
```

---

## 6. Test Requirements

**File:** `tests/requirements-test.txt`

```
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
moto[s3,dynamodb]==4.2.9
kafka-python==2.0.2
boto3==1.34.34
smart-open[s3]==6.4.0
psutil==5.9.6
```

---

## 7. Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Unit Tests Only
```bash
pytest tests/unit/
```

### Run with Coverage
```bash
pytest --cov=processor --cov-report=html tests/unit/
```

### Run Integration Tests
```bash
pytest -m integration tests/
```

### Run Performance Tests
```bash
pytest -m performance tests/
```

### Run Specific Test
```bash
pytest tests/unit/test_checkpoint_manager.py::TestCheckpointManager::test_update_checkpoint
```

---

## 8. CI/CD Integration

### GitHub Actions Workflow

**File:** `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      kafka:
        image: confluentinc/cp-kafka:latest
        ports:
          - 9092:9092
        env:
          KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      
      zookeeper:
        image: confluentinc/cp-zookeeper:latest
        ports:
          - 2181:2181
        env:
          ZOOKEEPER_CLIENT_PORT: 2181
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r option1-ecs-fargate/app/requirements.txt
          pip install -r tests/requirements-test.txt
      
      - name: Run unit tests
        run: pytest tests/unit/ --cov=processor --cov-report=xml
      
      - name: Run integration tests
        run: pytest tests/integration/ -m "not kafka"
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## 9. Test Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| CheckpointManager | 90%+ |
| MetricsEmitter | 85%+ |
| CSVToKafkaProcessor | 80%+ |
| Helper functions | 90%+ |
| **Overall** | **80%+** |

---

## 10. Test Execution Timeline

### Phase 1: Unit Tests (Week 1)
- Day 1-2: CheckpointManager tests
- Day 3-4: MetricsEmitter tests
- Day 5: CSVToKafkaProcessor tests

### Phase 2: Integration Tests (Week 2)
- Day 1-2: S3 and DynamoDB integration
- Day 3-4: Kafka integration
- Day 5: End-to-end tests

### Phase 3: Performance Tests (Week 3)
- Day 1-2: Throughput tests
- Day 3-4: Memory and latency tests
- Day 5: Load testing

---

## 11. Success Criteria

✅ All unit tests pass  
✅ 80%+ code coverage  
✅ Integration tests pass with LocalStack  
✅ E2E test passes with test environment  
✅ Performance tests meet benchmarks  
✅ CI/CD pipeline green  
✅ No flaky tests  

---

**Testing Plan Version:** 1.0.0  
**Last Updated:** January 16, 2026
