"""
Integration tests for S3 functionality
Uses moto to mock AWS S3 service
"""
import pytest
import boto3
from moto import mock_s3
import csv
import io
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../option1-ecs-fargate/app'))
from processor import CSVToKafkaProcessor


class TestS3Integration:
    """Integration tests for S3 operations"""
    
    @mock_s3
    def test_read_csv_from_s3(self):
        """Test reading CSV file from S3 using smart_open"""
        from smart_open import open as smart_open
        
        # Create S3 client and bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-csv-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create test CSV data
        csv_content = io.StringIO()
        writer = csv.DictWriter(csv_content, fieldnames=['id', 'name', 'email', 'value'])
        writer.writeheader()
        
        # Write 100 test records
        for i in range(100):
            writer.writerow({
                'id': str(i + 1),
                'name': f'User {i + 1}',
                'email': f'user{i + 1}@example.com',
                'value': str((i + 1) * 10)
            })
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key='test-data.csv',
            Body=csv_content.getvalue().encode('utf-8')
        )

        # Act - Read CSV from S3
        s3_uri = f's3://{bucket_name}/test-data.csv'
        rows = []
        
        with smart_open(s3_uri, 'r', transport_params={'client': s3_client}) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Assert
        assert len(rows) == 100
        assert rows[0]['id'] == '1'
        assert rows[0]['name'] == 'User 1'
        assert rows[0]['email'] == 'user1@example.com'
        assert rows[0]['value'] == '10'
        
        assert rows[99]['id'] == '100'
        assert rows[99]['name'] == 'User 100'
        assert rows[99]['value'] == '1000'
    
    @mock_s3
    def test_get_total_lines_from_s3(self):
        """Test counting total lines in S3 CSV file"""
        from unittest.mock import Mock, patch
        
        # Create S3 client and bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-csv-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create test CSV data
        csv_content = io.StringIO()
        writer = csv.DictWriter(csv_content, fieldnames=['id', 'name', 'email', 'value'])
        writer.writeheader()
        
        # Write 100 test records
        for i in range(100):
            writer.writerow({
                'id': str(i + 1),
                'name': f'User {i + 1}',
                'email': f'user{i + 1}@example.com',
                'value': str((i + 1) * 10)
            })
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key='test-data.csv',
            Body=csv_content.getvalue().encode('utf-8')
        )

        # Create mock checkpoint manager
        mock_checkpoint = Mock()
        mock_checkpoint.table.get_item.side_effect = Exception("Not cached")
        mock_checkpoint.table.put_item.return_value = None
        
        # Mock Kafka producer to avoid initialization
        with patch('processor.KafkaProducer'):
            # Create processor
            processor = CSVToKafkaProcessor(
                s3_bucket=bucket_name,
                s3_key='test-data.csv',
                kafka_bootstrap_servers='localhost:9092',
                kafka_topic='test-topic',
                checkpoint_manager=mock_checkpoint
            )
            
            # Override s3_client to use our mocked one
            processor.s3_client = s3_client
            
            # Act
            total_lines = processor._get_total_lines()
            
            # Assert
            assert total_lines == 101  # 100 data rows + 1 header row
            
            # Verify caching was attempted
            mock_checkpoint.table.put_item.assert_called_once()
            cache_call = mock_checkpoint.table.put_item.call_args[1]
            assert cache_call['Item']['total_lines'] == 101
    
    @mock_s3
    def test_s3_file_not_found(self):
        """Test handling of non-existent S3 file"""
        from unittest.mock import Mock, patch
        
        # Create S3 client and bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-csv-bucket'
        s3_client.create_bucket(Bucket=bucket_name)

        # Create mock checkpoint manager
        mock_checkpoint = Mock()
        mock_checkpoint.table.get_item.side_effect = Exception("Not cached")
        
        # Mock Kafka producer to avoid initialization
        with patch('processor.KafkaProducer'):
            # Create processor with non-existent file
            processor = CSVToKafkaProcessor(
                s3_bucket=bucket_name,
                s3_key='non-existent.csv',
                kafka_bootstrap_servers='localhost:9092',
                kafka_topic='test-topic',
                checkpoint_manager=mock_checkpoint
            )
            
            # Override s3_client to use our mocked one
            processor.s3_client = s3_client
            
            # Act & Assert
            total_lines = processor._get_total_lines()
            assert total_lines is None  # Should return None on error
    
    @mock_s3
    def test_s3_empty_file(self):
        """Test handling of empty S3 file"""
        from unittest.mock import Mock, patch
        
        # Create S3 client and bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-csv-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create empty CSV file
        s3_client.put_object(
            Bucket=bucket_name,
            Key='empty.csv',
            Body=b''
        )

        # Create mock checkpoint manager
        mock_checkpoint = Mock()
        mock_checkpoint.table.get_item.side_effect = Exception("Not cached")
        mock_checkpoint.table.put_item.return_value = None
        
        # Mock Kafka producer to avoid initialization
        with patch('processor.KafkaProducer'):
            # Create processor
            processor = CSVToKafkaProcessor(
                s3_bucket=bucket_name,
                s3_key='empty.csv',
                kafka_bootstrap_servers='localhost:9092',
                kafka_topic='test-topic',
                checkpoint_manager=mock_checkpoint
            )
            
            # Override s3_client to use our mocked one
            processor.s3_client = s3_client
            
            # Act
            total_lines = processor._get_total_lines()
            
            # Assert
            assert total_lines == 0  # Empty file has 0 lines
    
    @mock_s3
    def test_s3_large_file_streaming(self):
        """Test streaming read of larger S3 file"""
        from smart_open import open as smart_open
        
        # Create S3 client and bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-csv-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create larger CSV file (1000 rows)
        csv_content = io.StringIO()
        writer = csv.DictWriter(csv_content, fieldnames=['id', 'data'])
        writer.writeheader()
        
        for i in range(1000):
            writer.writerow({
                'id': str(i + 1),
                'data': f'Large data row {i + 1} with some content to make it bigger'
            })
        
        # Upload large file
        s3_client.put_object(
            Bucket=bucket_name,
            Key='large-data.csv',
            Body=csv_content.getvalue().encode('utf-8')
        )
        
        # Act - Stream read (should not load entire file into memory)
        s3_uri = f's3://{bucket_name}/large-data.csv'
        row_count = 0
        first_row = None
        last_row = None
        
        with smart_open(s3_uri, 'r', transport_params={'client': s3_client}) as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_count += 1
                if first_row is None:
                    first_row = row
                last_row = row
        
        # Assert
        assert row_count == 1000
        assert first_row['id'] == '1'
        assert last_row['id'] == '1000'
        assert 'Large data row 1000' in last_row['data']


@pytest.mark.integration
class TestS3IntegrationMarked:
    """Integration tests marked for selective execution"""
    
    @mock_s3
    def test_s3_integration_workflow(self):
        """Complete S3 integration test workflow"""
        # This test demonstrates the integration test pattern
        # and can be run with: pytest -m integration
        
        # Setup
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'integration-test-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create test data
        csv_content = "id,name,value\n1,Test,100\n2,Test2,200\n"
        s3_client.put_object(
            Bucket=bucket_name,
            Key='integration-test.csv',
            Body=csv_content.encode('utf-8')
        )
        
        # Test reading
        from smart_open import open as smart_open
        s3_uri = f's3://{bucket_name}/integration-test.csv'
        
        with smart_open(s3_uri, 'r', transport_params={'client': s3_client}) as f:
            content = f.read()
        
        assert 'Test,100' in content
        assert 'Test2,200' in content