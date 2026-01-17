"""
Unit tests for CSVToKafkaProcessor class
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from kafka.errors import KafkaError
from moto import mock_s3, mock_dynamodb
import boto3
import csv
import io
import sys
import os
import time

# Add parent directory to path to import processor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../option1-ecs-fargate/app'))
from processor import CSVToKafkaProcessor, CheckpointManager, MetricsEmitter


class TestCSVToKafkaProcessor:
    """Test suite for CSVToKafkaProcessor"""
    
    @pytest.fixture
    def mock_kafka_dependencies(self):
        """Mock Kafka dependencies only"""
        with patch('processor.KafkaProducer') as mock_kafka:
            yield mock_kafka
    
    @pytest.fixture
    def mock_checkpoint_manager(self):
        """Mock CheckpointManager"""
        mock = Mock(spec=CheckpointManager)
        mock.get_last_processed_line.return_value = 0
        mock.table = Mock()
        return mock
    
    @pytest.fixture
    def mock_metrics_emitter(self):
        """Mock MetricsEmitter"""
        return Mock(spec=MetricsEmitter)
    
    @pytest.fixture
    @mock_s3
    def s3_setup(self):
        """Setup S3 bucket with test CSV data using moto"""
        # Create S3 client and bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-csv-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        return s3_client, bucket_name
    
    def test_init(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test CSVToKafkaProcessor initialization"""
        # Arrange & Act
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager,
            checkpoint_interval=5000,
            total_lines=100000
        )
        
        # Assert
        assert processor.s3_bucket == 'test-bucket'
        assert processor.s3_key == 'test.csv'
        assert processor.kafka_topic == 'test-topic'
        assert processor.checkpoint_interval == 5000
        assert processor.total_lines == 100000
        assert processor.error_count == 0
        assert processor.retry_count == 0
    
    def test_init_with_metrics(self, mock_kafka_dependencies, mock_checkpoint_manager, mock_metrics_emitter):
        """Test initialization with metrics emitter"""
        # Arrange & Act
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager,
            metrics_emitter=mock_metrics_emitter
        )
        
        # Assert
        assert processor.metrics == mock_metrics_emitter
    
    def test_calculate_eta_with_progress(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test ETA calculation with progress"""
        # Arrange
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager,
            total_lines=100000
        )
        
        # Simulate 10 seconds elapsed, 10000 records processed
        processor.start_time = time.time() - 10
        
        # Act
        eta = processor._calculate_eta(10000)
        
        # Assert
        # Rate: 10000/10 = 1000 rec/sec
        # Remaining: 90000
        # ETA: 90000/1000 = 90 seconds
        assert eta == pytest.approx(90.0, rel=0.1)
    
    def test_calculate_eta_no_total_lines(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test ETA returns 0 when total lines unknown"""
        # Arrange
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager,
            total_lines=None
        )
        
        # Act
        eta = processor._calculate_eta(10000)
        
        # Assert
        assert eta == 0
    
    def test_calculate_eta_zero_current_line(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test ETA returns 0 when no lines processed yet"""
        # Arrange
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager,
            total_lines=100000
        )
        
        # Act
        eta = processor._calculate_eta(0)
        
        # Assert
        assert eta == 0
    
    @mock_s3
    def test_get_total_lines_cached(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test total lines retrieved from cache"""
        # Arrange
        mock_checkpoint_manager.table.get_item.return_value = {
            'Item': {'total_lines': 50000}
        }
        
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager
        )
        
        # Act
        total = processor._get_total_lines()
        
        # Assert
        assert total == 50000
        mock_checkpoint_manager.table.get_item.assert_called_once()
    
    @mock_s3
    def test_get_total_lines_count(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test total lines counted when not cached"""
        # Arrange
        mock_checkpoint_manager.table.get_item.side_effect = Exception("Not found")
        
        # Create S3 bucket and CSV file
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create CSV content with 100 lines
        csv_content = io.StringIO()
        writer = csv.DictWriter(csv_content, fieldnames=['id', 'name'])
        writer.writeheader()
        for i in range(100):
            writer.writerow({'id': str(i), 'name': f'item-{i}'})
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key='test.csv',
            Body=csv_content.getvalue().encode('utf-8')
        )
        
        processor = CSVToKafkaProcessor(
            s3_bucket=bucket_name,
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager
        )
        
        # Override s3_client to use mocked one
        processor.s3_client = s3_client
        
        # Act
        total = processor._get_total_lines()
        
        # Assert
        assert total == 101  # 100 data rows + 1 header
        mock_checkpoint_manager.table.put_item.assert_called_once()
        
        # Verify cache was saved
        call_args = mock_checkpoint_manager.table.put_item.call_args[1]
        assert call_args['Item']['total_lines'] == 101
    
    @mock_s3
    def test_get_total_lines_error(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test total lines returns None on error"""
        # Arrange
        mock_checkpoint_manager.table.get_item.side_effect = Exception("Not found")
        
        # Don't create the S3 file - this will cause an error
        processor = CSVToKafkaProcessor(
            s3_bucket='non-existent-bucket',
            s3_key='non-existent.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager
        )
        
        # Act
        total = processor._get_total_lines()
        
        # Assert
        assert total is None
    
    def test_send_to_kafka_success(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test successful Kafka send"""
        # Arrange
        mock_producer = Mock()
        mock_future = Mock()
        mock_metadata = Mock()
        mock_metadata.partition = 0
        mock_metadata.offset = 12345
        mock_future.get.return_value = mock_metadata
        mock_producer.send.return_value = mock_future
        mock_kafka_dependencies.return_value = mock_producer
        
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager
        )
        
        # Act
        row = {'id': '1', 'name': 'test', 'value': '100'}
        result = processor._send_to_kafka(row, 1)
        
        # Assert
        assert result is True
        mock_producer.send.assert_called_once()
        
        # Verify enriched data
        call_args = mock_producer.send.call_args[1]
        assert call_args['value']['_source_line'] == 1
        assert call_args['value']['_source_file'] == 's3://test-bucket/test.csv'
        assert call_args['partition'] == 0
    
    def test_send_to_kafka_retry_success(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test Kafka send succeeds after retry"""
        # Arrange
        mock_producer = Mock()
        mock_future = Mock()
        mock_metadata = Mock()
        mock_metadata.partition = 0
        mock_metadata.offset = 12345
        
        # Fail first time, succeed second time
        mock_future.get.side_effect = [
            KafkaError("Temporary error"),
            mock_metadata
        ]
        mock_producer.send.return_value = mock_future
        mock_kafka_dependencies.return_value = mock_producer
        
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager
        )
        
        # Act
        row = {'id': '1', 'name': 'test'}
        result = processor._send_to_kafka(row, 1, max_retries=5)
        
        # Assert
        assert result is True
        assert processor.retry_count == 1
        assert mock_producer.send.call_count == 2
    
    def test_send_to_kafka_max_retries_exceeded(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test Kafka send fails after max retries"""
        # Arrange
        mock_producer = Mock()
        mock_future = Mock()
        mock_future.get.side_effect = KafkaError("Persistent error")
        mock_producer.send.return_value = mock_future
        mock_kafka_dependencies.return_value = mock_producer
        
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager
        )
        
        # Act
        row = {'id': '1', 'name': 'test'}
        result = processor._send_to_kafka(row, 1, max_retries=3)
        
        # Assert
        assert result is False
        assert processor.retry_count == 3
        assert mock_producer.send.call_count == 3
    
    def test_send_to_kafka_unexpected_error(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test Kafka send handles unexpected errors"""
        # Arrange
        mock_producer = Mock()
        mock_producer.send.side_effect = Exception("Unexpected error")
        mock_kafka_dependencies.return_value = mock_producer
        
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager
        )
        
        # Act
        row = {'id': '1', 'name': 'test'}
        result = processor._send_to_kafka(row, 1)
        
        # Assert
        assert result is False
    
    @mock_s3
    def test_process_skip_already_processed_lines(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test process skips already processed lines"""
        # Arrange
        mock_checkpoint_manager.get_last_processed_line.return_value = 5
        
        # Create S3 bucket and CSV file
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create CSV content with 10 rows
        csv_content = io.StringIO()
        writer = csv.DictWriter(csv_content, fieldnames=['id', 'name'])
        writer.writeheader()
        for i in range(10):
            writer.writerow({'id': str(i), 'name': f'item-{i}'})
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key='test.csv',
            Body=csv_content.getvalue().encode('utf-8')
        )
        
        # Mock Kafka producer
        mock_producer = Mock()
        mock_future = Mock()
        mock_metadata = Mock()
        mock_metadata.partition = 0
        mock_metadata.offset = 1
        mock_future.get.return_value = mock_metadata
        mock_producer.send.return_value = mock_future
        mock_kafka_dependencies.return_value = mock_producer
        
        processor = CSVToKafkaProcessor(
            s3_bucket=bucket_name,
            s3_key='test.csv',
            kafka_bootstrap_servers='localhost:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager,
            checkpoint_interval=100,
            total_lines=10
        )
        
        # Override s3_client to use mocked one
        processor.s3_client = s3_client
        
        # Act
        processor.process()
        
        # Assert - Should only send 5 records (lines 6-10)
        assert mock_producer.send.call_count == 5
        mock_checkpoint_manager.mark_complete.assert_called_once_with(10)
    
    def test_kafka_producer_configuration(self, mock_kafka_dependencies, mock_checkpoint_manager):
        """Test Kafka producer is configured correctly"""
        # Arrange & Act
        processor = CSVToKafkaProcessor(
            s3_bucket='test-bucket',
            s3_key='test.csv',
            kafka_bootstrap_servers='broker1:9092,broker2:9092',
            kafka_topic='test-topic',
            checkpoint_manager=mock_checkpoint_manager
        )
        
        # Assert
        mock_kafka_dependencies.assert_called_once()
        call_kwargs = mock_kafka_dependencies.call_args[1]
        
        # Verify ordering guarantees
        assert call_kwargs['max_in_flight_requests_per_connection'] == 1
        assert call_kwargs['acks'] == 'all'
        assert call_kwargs['enable_idempotency'] is True
        
        # Verify reliability settings
        assert call_kwargs['retries'] == 2147483647
        assert call_kwargs['max_block_ms'] == 60000
        
        # Verify bootstrap servers
        assert call_kwargs['bootstrap_servers'] == ['broker1:9092', 'broker2:9092']
