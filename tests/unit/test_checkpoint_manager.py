"""
Unit tests for CheckpointManager class
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from moto import mock_dynamodb
import boto3
import sys
import os

# Add parent directory to path to import processor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../option1-ecs-fargate/app'))
from processor import CheckpointManager


class TestCheckpointManager:
    """Test suite for CheckpointManager"""
    
    @pytest.fixture
    @mock_dynamodb
    def dynamodb_table(self):
        """Create a real DynamoDB table using moto"""
        # Create DynamoDB resource
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create table
        table = dynamodb.create_table(
            TableName='test-checkpoint-table',
            KeySchema=[
                {'AttributeName': 'job_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'job_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to be created
        table.wait_until_exists()
        return table
    
    @mock_dynamodb
    def test_init(self):
        """Test CheckpointManager initialization"""
        # Arrange & Act
        manager = CheckpointManager('test-checkpoint-table', 'test-job')
        
        # Assert
        assert manager.job_id == 'test-job'
        assert manager.table.table_name == 'test-checkpoint-table'
    
    @mock_dynamodb
    def test_get_last_processed_line_exists(self):
        """Test retrieving existing checkpoint"""
        # Arrange
        # Create DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-checkpoint-table',
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        
        # Put an item in the table first
        table.put_item(Item={
            'job_id': 'test-job',
            'last_line': 5000,
            'total_sent': 5000,
            'timestamp': 1234567890
        })
        
        manager = CheckpointManager('test-checkpoint-table', 'test-job')
        
        # Act
        result = manager.get_last_processed_line()
        
        # Assert
        assert result == 5000
    
    @mock_dynamodb
    def test_get_last_processed_line_not_exists(self):
        """Test retrieving non-existent checkpoint returns 0"""
        # Arrange
        # Create DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-checkpoint-table',
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        
        manager = CheckpointManager('test-checkpoint-table', 'non-existent-job')
        
        # Act
        result = manager.get_last_processed_line()
        
        # Assert
        assert result == 0
    
    def test_get_last_processed_line_table_not_exists(self):
        """Test error handling when table doesn't exist"""
        # Arrange - Don't create the table
        manager = CheckpointManager('non-existent-table', 'test-job')
        
        # Act
        result = manager.get_last_processed_line()
        
        # Assert - Should return 0 on error
        assert result == 0
    
    @mock_dynamodb
    def test_update_checkpoint(self):
        """Test updating checkpoint"""
        # Arrange
        # Create DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-checkpoint-table',
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        
        manager = CheckpointManager('test-checkpoint-table', 'test-job')
        
        # Act
        manager.update_checkpoint(10000, 10000)
        
        # Assert - Verify item was stored
        response = table.get_item(Key={'job_id': 'test-job'})
        assert 'Item' in response
        item = response['Item']
        assert item['job_id'] == 'test-job'
        assert item['last_line'] == 10000
        assert item['total_sent'] == 10000
        assert 'timestamp' in item
    
    def test_update_checkpoint_table_not_exists(self):
        """Test error handling when updating checkpoint on non-existent table"""
        # Arrange - Don't create the table
        manager = CheckpointManager('non-existent-table', 'test-job')
        
        # Act & Assert - Should raise exception
        with pytest.raises(ClientError):
            manager.update_checkpoint(10000, 10000)
    
    @mock_dynamodb
    def test_mark_complete(self):
        """Test marking job as complete"""
        # Arrange
        # Create DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-checkpoint-table',
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        
        manager = CheckpointManager('test-checkpoint-table', 'test-job')
        
        # Act
        manager.mark_complete(100000)
        
        # Assert - Verify completion was stored
        response = table.get_item(Key={'job_id': 'test-job'})
        assert 'Item' in response
        item = response['Item']
        assert item['job_id'] == 'test-job'
        assert item['last_line'] == 100000
        assert item['total_sent'] == 100000
        assert item['status'] == 'COMPLETED'
        assert 'timestamp' in item
    
    def test_mark_complete_table_not_exists(self):
        """Test error handling when marking complete on non-existent table"""
        # Arrange - Don't create the table
        manager = CheckpointManager('non-existent-table', 'test-job')
        
        # Act & Assert - Should raise exception
        with pytest.raises(ClientError):
            manager.mark_complete(100000)
    
    @mock_dynamodb
    def test_checkpoint_workflow(self):
        """Test complete checkpoint workflow"""
        # Arrange
        # Create DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-checkpoint-table',
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        
        manager = CheckpointManager('test-checkpoint-table', 'workflow-job')
        
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
        response = table.get_item(Key={'job_id': 'workflow-job'})
        item = response['Item']
        assert item['status'] == 'COMPLETED'
        assert item['last_line'] == 10000
    
    @mock_dynamodb
    def test_multiple_jobs(self):
        """Test multiple jobs can use same table"""
        # Arrange
        # Create DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-checkpoint-table',
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        
        manager1 = CheckpointManager('test-checkpoint-table', 'job-1')
        manager2 = CheckpointManager('test-checkpoint-table', 'job-2')
        
        # Act
        manager1.update_checkpoint(1000, 1000)
        manager2.update_checkpoint(2000, 2000)
        
        # Assert
        assert manager1.get_last_processed_line() == 1000
        assert manager2.get_last_processed_line() == 2000
    
    @mock_dynamodb
    def test_checkpoint_overwrite(self):
        """Test checkpoint can be overwritten"""
        # Arrange
        # Create DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='test-checkpoint-table',
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        
        manager = CheckpointManager('test-checkpoint-table', 'overwrite-job')
        
        # Act
        manager.update_checkpoint(1000, 1000)
        assert manager.get_last_processed_line() == 1000
        
        # Overwrite with new values
        manager.update_checkpoint(2000, 2000)
        assert manager.get_last_processed_line() == 2000
        
        # Assert - Should have latest values
        response = table.get_item(Key={'job_id': 'overwrite-job'})
        item = response['Item']
        assert item['last_line'] == 2000
        assert item['total_sent'] == 2000
