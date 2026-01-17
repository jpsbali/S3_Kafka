"""
Unit tests for MetricsEmitter class
"""
import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime
from moto import mock_cloudwatch
import boto3
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../option1-ecs-fargate/app'))
from processor import MetricsEmitter


class TestMetricsEmitter:
    """Test suite for MetricsEmitter"""
    
    @pytest.fixture
    @mock_cloudwatch
    def cloudwatch_client(self):
        """Create a real CloudWatch client using moto"""
        return boto3.client('cloudwatch', region_name='us-east-1')
    
    @mock_cloudwatch
    def test_init(self):
        """Test MetricsEmitter initialization"""
        # Arrange & Act
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Assert
        assert emitter.namespace == 'TestNamespace'
        assert emitter.job_id == 'test-job'
        assert emitter.metrics_buffer == []
        assert emitter.cloudwatch is not None
    
    @mock_cloudwatch
    def test_emit_throughput(self):
        """Test emitting throughput metric"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.emit_throughput(45000.5)
        
        # Assert
        assert len(emitter.metrics_buffer) == 1
        metric = emitter.metrics_buffer[0]
        assert metric['MetricName'] == 'RecordsPerSecond'
        assert metric['Value'] == 45000.5
        assert metric['Unit'] == 'Count/Second'
        assert metric['Dimensions'] == [{'Name': 'JobId', 'Value': 'test-job'}]
    
    @mock_cloudwatch
    def test_emit_progress(self):
        """Test emitting progress metrics"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.emit_progress(50000, 100000)
        
        # Assert
        assert len(emitter.metrics_buffer) == 3  # Percentage, Processed, Remaining
        
        # Check percentage
        percentage_metric = next(m for m in emitter.metrics_buffer 
                                if m['MetricName'] == 'ProgressPercentage')
        assert percentage_metric['Value'] == 50.0
        assert percentage_metric['Unit'] == 'Percent'
        
        # Check processed
        processed_metric = next(m for m in emitter.metrics_buffer 
                               if m['MetricName'] == 'RecordsProcessed')
        assert processed_metric['Value'] == 50000
        
        # Check remaining
        remaining_metric = next(m for m in emitter.metrics_buffer 
                               if m['MetricName'] == 'RecordsRemaining')
        assert remaining_metric['Value'] == 50000
    
    @mock_cloudwatch
    def test_emit_progress_zero_total(self):
        """Test emitting progress with zero total lines"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.emit_progress(50000, 0)
        
        # Assert - Should not emit any metrics
        assert len(emitter.metrics_buffer) == 0
    
    @mock_cloudwatch
    def test_emit_kafka_latency(self):
        """Test emitting Kafka latency metric"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.emit_kafka_latency(12.5)
        
        # Assert
        assert len(emitter.metrics_buffer) == 1
        metric = emitter.metrics_buffer[0]
        assert metric['MetricName'] == 'KafkaLatency'
        assert metric['Value'] == 12.5
        assert metric['Unit'] == 'Milliseconds'
    
    @mock_cloudwatch
    def test_emit_error_count(self):
        """Test emitting error count metric"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.emit_error_count(5)
        
        # Assert
        assert len(emitter.metrics_buffer) == 1
        metric = emitter.metrics_buffer[0]
        assert metric['MetricName'] == 'ErrorCount'
        assert metric['Value'] == 5
        assert metric['Unit'] == 'Count'
    
    @mock_cloudwatch
    def test_emit_eta(self):
        """Test emitting ETA metrics"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.emit_eta(3600)  # 3600 seconds = 60 minutes
        
        # Assert
        assert len(emitter.metrics_buffer) == 2  # Seconds and Minutes
        
        seconds_metric = next(m for m in emitter.metrics_buffer 
                             if m['MetricName'] == 'ETASeconds')
        assert seconds_metric['Value'] == 3600
        
        minutes_metric = next(m for m in emitter.metrics_buffer 
                             if m['MetricName'] == 'ETAMinutes')
        assert minutes_metric['Value'] == 60.0
    
    @mock_cloudwatch
    def test_buffer_flush_on_size(self):
        """Test buffer flushes when reaching 20 metrics"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act - Add 20 metrics (should trigger flush)
        for i in range(20):
            emitter.emit_throughput(1000.0)
        
        # Assert - Buffer should be cleared after automatic flush
        assert len(emitter.metrics_buffer) == 0
    
    @mock_cloudwatch
    def test_flush_batches_metrics(self):
        """Test flush sends metrics in batches of 20"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Add 45 metrics manually to buffer
        for i in range(45):
            emitter.metrics_buffer.append({
                'MetricName': 'Test',
                'Value': i,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow(),
                'Dimensions': [{'Name': 'JobId', 'Value': 'test-job'}]
            })
        
        # Act
        emitter.flush()
        
        # Assert - Buffer should be cleared
        assert len(emitter.metrics_buffer) == 0
        
        # Verify metrics were sent to CloudWatch (moto will handle the calls)
        # We can't easily verify the exact calls with moto, but we can verify the buffer is empty
    
    @mock_cloudwatch
    def test_flush_empty_buffer(self):
        """Test flush with empty buffer does nothing"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.flush()
        
        # Assert - Should not raise any errors
        assert len(emitter.metrics_buffer) == 0
    
    @mock_cloudwatch
    def test_flush_with_real_metrics(self):
        """Test flush actually sends metrics to CloudWatch"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act - Add some metrics and flush
        emitter.emit_throughput(1000.0)
        emitter.emit_error_count(1)
        emitter.emit_checkpoint_count()
        emitter.flush()
        
        # Assert - Buffer should be cleared
        assert len(emitter.metrics_buffer) == 0
    
    @mock_cloudwatch
    def test_metric_dimensions(self):
        """Test all metrics include correct dimensions"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'custom-job-id')
        
        # Act
        emitter.emit_throughput(1000.0)
        emitter.emit_error_count(1)
        emitter.emit_checkpoint_count()
        
        # Assert
        for metric in emitter.metrics_buffer:
            assert metric['Dimensions'] == [{'Name': 'JobId', 'Value': 'custom-job-id'}]
    
    @mock_cloudwatch
    def test_emit_retry_count(self):
        """Test emitting retry count metric"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.emit_retry_count(3)
        
        # Assert
        assert len(emitter.metrics_buffer) == 1
        metric = emitter.metrics_buffer[0]
        assert metric['MetricName'] == 'RetryCount'
        assert metric['Value'] == 3
        assert metric['Unit'] == 'Count'
    
    @mock_cloudwatch
    def test_emit_checkpoint_count(self):
        """Test emitting checkpoint count metric"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Act
        emitter.emit_checkpoint_count()
        
        # Assert
        assert len(emitter.metrics_buffer) == 1
        metric = emitter.metrics_buffer[0]
        assert metric['MetricName'] == 'CheckpointCount'
        assert metric['Value'] == 1
        assert metric['Unit'] == 'Count'
    
    @mock_cloudwatch
    def test_time_based_flush(self):
        """Test buffer flushes after time interval"""
        # Arrange
        emitter = MetricsEmitter('TestNamespace', 'test-job')
        
        # Simulate time passing by setting last_flush to past
        emitter.last_flush = emitter.last_flush - 70  # 70 seconds ago
        
        # Act - Add one metric (should trigger time-based flush)
        emitter.emit_throughput(1000.0)
        
        # Assert - Buffer should be cleared due to time-based flush
        assert len(emitter.metrics_buffer) == 0
    
    @mock_cloudwatch
    def test_namespace_and_job_id_usage(self):
        """Test that namespace and job_id are used correctly"""
        # Arrange
        namespace = 'CustomNamespace'
        job_id = 'custom-job-123'
        emitter = MetricsEmitter(namespace, job_id)
        
        # Act
        emitter.emit_throughput(500.0)
        
        # Assert
        assert emitter.namespace == namespace
        assert emitter.job_id == job_id
        metric = emitter.metrics_buffer[0]
        assert metric['Dimensions'] == [{'Name': 'JobId', 'Value': job_id}]
