#!/usr/bin/env python3
"""
CSV to Kafka Processor with Guaranteed Delivery and Metrics
Processes CSV from S3 sequentially and sends to Kafka with checkpointing
Emits CloudWatch metrics for real-time monitoring
"""

import os
import sys
import csv
import json
import time
import logging
from typing import Dict, Optional
from datetime import datetime
import boto3
from kafka import KafkaProducer
from kafka.errors import KafkaError
from smart_open import open as smart_open
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetricsEmitter:
    """Emits CloudWatch metrics for monitoring"""
    
    def __init__(self, namespace: str = 'CSVToKafka', job_id: str = 'csv-job-1'):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
        self.job_id = job_id
        self.metrics_buffer = []
        self.last_flush = time.time()
    
    def emit_throughput(self, records_per_second: float):
        """Emit throughput metric"""
        self._add_metric('RecordsPerSecond', records_per_second, 'Count/Second')
    
    def emit_progress(self, current_line: int, total_lines: int):
        """Emit progress percentage"""
        if total_lines > 0:
            percentage = (current_line / total_lines) * 100
            self._add_metric('ProgressPercentage', percentage, 'Percent')
            self._add_metric('RecordsProcessed', current_line, 'Count')
            self._add_metric('RecordsRemaining', total_lines - current_line, 'Count')
    
    def emit_kafka_latency(self, latency_ms: float):
        """Emit Kafka send latency"""
        self._add_metric('KafkaLatency', latency_ms, 'Milliseconds')
    
    def emit_error_count(self, error_count: int):
        """Emit error count"""
        self._add_metric('ErrorCount', error_count, 'Count')
    
    def emit_retry_count(self, retry_count: int):
        """Emit retry count"""
        self._add_metric('RetryCount', retry_count, 'Count')
    
    def emit_eta(self, eta_seconds: float):
        """Emit estimated time to completion"""
        self._add_metric('ETASeconds', eta_seconds, 'Seconds')
        self._add_metric('ETAMinutes', eta_seconds / 60, 'None')
    
    def emit_checkpoint_count(self):
        """Emit checkpoint saved count"""
        self._add_metric('CheckpointCount', 1, 'Count')
    
    def _add_metric(self, metric_name: str, value: float, unit: str):
        """Add metric to buffer"""
        self.metrics_buffer.append({
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow(),
            'Dimensions': [{'Name': 'JobId', 'Value': self.job_id}]
        })
        
        # Flush if buffer is large or time elapsed
        if len(self.metrics_buffer) >= 20 or (time.time() - self.last_flush) > 60:
            self.flush()
    
    def flush(self):
        """Flush metrics buffer to CloudWatch"""
        if not self.metrics_buffer:
            return
        
        try:
            # CloudWatch allows max 20 metrics per call
            for i in range(0, len(self.metrics_buffer), 20):
                batch = self.metrics_buffer[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
            
            logger.debug(f"Flushed {len(self.metrics_buffer)} metrics to CloudWatch")
            self.metrics_buffer = []
            self.last_flush = time.time()
        except Exception as e:
            logger.warning(f"Failed to emit metrics: {e}")
            self.metrics_buffer = []  # Clear buffer to prevent memory issues

class CheckpointManager:
    """Manages checkpointing in DynamoDB"""
    
    def __init__(self, table_name: str, job_id: str):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self.job_id = job_id
    
    def get_last_processed_line(self) -> int:
        """Get the last successfully processed line number"""
        try:
            response = self.table.get_item(Key={'job_id': self.job_id})
            if 'Item' in response:
                return int(response['Item'].get('last_line', 0))
            return 0
        except ClientError as e:
            logger.error(f"Error reading checkpoint: {e}")
            return 0
    
    def update_checkpoint(self, line_number: int, total_sent: int):
        """Update checkpoint with current progress"""
        try:
            self.table.put_item(
                Item={
                    'job_id': self.job_id,
                    'last_line': line_number,
                    'total_sent': total_sent,
                    'timestamp': int(time.time())
                }
            )
        except ClientError as e:
            logger.error(f"Error updating checkpoint: {e}")
            raise
    
    def mark_complete(self, total_lines: int):
        """Mark job as complete"""
        try:
            self.table.put_item(
                Item={
                    'job_id': self.job_id,
                    'last_line': total_lines,
                    'total_sent': total_lines,
                    'status': 'COMPLETED',
                    'timestamp': int(time.time())
                }
            )
        except ClientError as e:
            logger.error(f"Error marking complete: {e}")
            raise


class CSVToKafkaProcessor:
    """Main processor class with metrics"""
    
    def __init__(
        self,
        s3_bucket: str,
        s3_key: str,
        kafka_bootstrap_servers: str,
        kafka_topic: str,
        checkpoint_manager: CheckpointManager,
        metrics_emitter: Optional[MetricsEmitter] = None,
        checkpoint_interval: int = 10000,
        total_lines: Optional[int] = None
    ):
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.kafka_topic = kafka_topic
        self.checkpoint_manager = checkpoint_manager
        self.checkpoint_interval = checkpoint_interval
        self.metrics = metrics_emitter
        self.total_lines = total_lines
        
        # Metrics tracking
        self.start_time = time.time()
        self.last_metric_time = time.time()
        self.records_since_last_metric = 0
        self.error_count = 0
        self.retry_count = 0
        
        # Initialize Kafka producer with guaranteed delivery settings
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers.split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            max_in_flight_requests_per_connection=1,  # Ensures ordering
            acks='all',  # Wait for all replicas
            retries=2147483647,  # Retry indefinitely
            max_block_ms=60000,  # Wait up to 60s for buffer space
            enable_idempotency=True,  # Prevents duplicates
            compression_type='gzip'
        )
        
        self.s3_client = boto3.client('s3')
    
    def _calculate_eta(self, current_line: int) -> float:
        """Calculate estimated time to completion in seconds"""
        if not self.total_lines or current_line == 0:
            return 0
        
        elapsed = time.time() - self.start_time
        rate = current_line / elapsed
        remaining = self.total_lines - current_line
        
        if rate > 0:
            return remaining / rate
        return 0
    
    def process(self):
        """Main processing loop with error handling and recovery"""
        start_line = self.checkpoint_manager.get_last_processed_line()
        logger.info(f"Starting from line {start_line}")
        
        # Get total lines if not provided
        if not self.total_lines:
            self.total_lines = self._get_total_lines()
        
        if self.total_lines:
            logger.info(f"Total lines in CSV: {self.total_lines}")
        
        s3_uri = f's3://{self.s3_bucket}/{self.s3_key}'
        current_line = 0
        records_sent = 0
        errors = []
        
        try:
            with smart_open(
                s3_uri, 
                'r', 
                transport_params={'client': self.s3_client}
            ) as s3_file:
                csv_reader = csv.DictReader(s3_file)
                
                for row in csv_reader:
                    current_line += 1
                    
                    # Skip already processed lines
                    if current_line <= start_line:
                        continue
                    
                    # Send to Kafka with retry logic and latency tracking
                    send_start = time.time()
                    success = self._send_to_kafka(row, current_line)
                    latency_ms = (time.time() - send_start) * 1000
                    
                    if not success:
                        error_msg = f"Failed to send line {current_line} after retries"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        self.error_count += 1
                        
                        if self.metrics:
                            self.metrics.emit_error_count(self.error_count)
                        
                        raise Exception(error_msg)
                    
                    records_sent += 1
                    self.records_since_last_metric += 1
                    
                    # Emit latency metric
                    if self.metrics:
                        self.metrics.emit_kafka_latency(latency_ms)
                    
                    # Emit throughput every 1000 records
                    if records_sent % 1000 == 0 and self.metrics:
                        elapsed = time.time() - self.last_metric_time
                        if elapsed > 0:
                            throughput = self.records_since_last_metric / elapsed
                            self.metrics.emit_throughput(throughput)
                            self.last_metric_time = time.time()
                            self.records_since_last_metric = 0
                    
                    # Checkpoint progress
                    if records_sent % self.checkpoint_interval == 0:
                        self.producer.flush()
                        self.checkpoint_manager.update_checkpoint(
                            current_line, 
                            records_sent
                        )
                        
                        # Emit progress and ETA metrics
                        if self.metrics:
                            self.metrics.emit_checkpoint_count()
                            if self.total_lines:
                                self.metrics.emit_progress(current_line, self.total_lines)
                                eta = self._calculate_eta(current_line)
                                self.metrics.emit_eta(eta)
                                logger.info(
                                    f"Progress: {records_sent} records sent "
                                    f"(line {current_line}/{self.total_lines}, "
                                    f"{(current_line/self.total_lines)*100:.1f}%, "
                                    f"ETA: {eta/60:.1f} min)"
                                )
                            else:
                                logger.info(
                                    f"Progress: {records_sent} records sent "
                                    f"(line {current_line})"
                                )
                            
                            if self.retry_count > 0:
                                self.metrics.emit_retry_count(self.retry_count)
                
                # Final flush and checkpoint
                self.producer.flush()
                self.checkpoint_manager.mark_complete(current_line)
                
                # Final metrics
                if self.metrics:
                    if self.total_lines:
                        self.metrics.emit_progress(current_line, self.total_lines)
                    self.metrics.flush()
                
                logger.info(
                    f"COMPLETED: {records_sent} records sent to Kafka. "
                    f"Total lines processed: {current_line}"
                )
                
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            # Save checkpoint before failing
            try:
                self.producer.flush()
                self.checkpoint_manager.update_checkpoint(
                    current_line, 
                    records_sent
                )
                if self.metrics:
                    self.metrics.flush()
            except Exception as checkpoint_error:
                logger.error(f"Failed to save checkpoint: {checkpoint_error}")
            raise
        
        finally:
            self.producer.close()
    
    def _get_total_lines(self) -> Optional[int]:
        """Get total lines in CSV (cached in DynamoDB)"""
        cache_key = f"linecount-{self.s3_bucket}/{self.s3_key}"
        
        try:
            # Check cache first
            response = self.checkpoint_manager.table.get_item(Key={'job_id': cache_key})
            if 'Item' in response:
                total = int(response['Item']['total_lines'])
                logger.info(f"Using cached line count: {total}")
                return total
        except Exception as e:
            logger.debug(f"No cached line count: {e}")
        
        # Count lines (expensive, do once)
        logger.info("Counting total lines in CSV (this may take a moment)...")
        try:
            s3_uri = f's3://{self.s3_bucket}/{self.s3_key}'
            total = 0
            with smart_open(s3_uri, 'r', transport_params={'client': self.s3_client}) as f:
                for _ in f:
                    total += 1
            
            # Cache result
            self.checkpoint_manager.table.put_item(Item={
                'job_id': cache_key,
                'total_lines': total,
                'timestamp': int(time.time())
            })
            
            logger.info(f"Total lines counted: {total}")
            return total
        except Exception as e:
            logger.warning(f"Could not count total lines: {e}")
            return None
    
    def _send_to_kafka(self, row: Dict, line_number: int, max_retries: int = 5) -> bool:
        """Send a single record to Kafka with retry logic"""
        for attempt in range(max_retries):
            try:
                # Add metadata to track source
                enriched_row = {
                    **row,
                    '_source_line': line_number,
                    '_source_file': f's3://{self.s3_bucket}/{self.s3_key}'
                }
                
                future = self.producer.send(
                    self.kafka_topic,
                    value=enriched_row,
                    partition=0  # Single partition for ordering
                )
                
                # Wait for confirmation with timeout
                record_metadata = future.get(timeout=30)
                
                logger.debug(
                    f"Line {line_number} sent to partition "
                    f"{record_metadata.partition} offset {record_metadata.offset}"
                )
                return True
                
            except KafkaError as e:
                self.retry_count += 1
                logger.warning(
                    f"Kafka error on line {line_number}, "
                    f"attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to send line {line_number} after {max_retries} attempts")
                    return False
            
            except Exception as e:
                logger.error(f"Unexpected error sending line {line_number}: {e}")
                return False
        
        return False


def main():
    """Main entry point"""
    # Get configuration from environment
    s3_bucket = os.environ.get('S3_BUCKET')
    s3_key = os.environ.get('S3_KEY')
    kafka_bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS')
    kafka_topic = os.environ.get('KAFKA_TOPIC')
    dynamodb_table = os.environ.get('DYNAMODB_TABLE')
    job_id = os.environ.get('JOB_ID', 'csv-job-1')
    enable_metrics = os.environ.get('ENABLE_METRICS', 'true').lower() == 'true'
    
    # Validate configuration
    required_vars = {
        'S3_BUCKET': s3_bucket,
        'S3_KEY': s3_key,
        'KAFKA_BOOTSTRAP_SERVERS': kafka_bootstrap_servers,
        'KAFKA_TOPIC': kafka_topic,
        'DYNAMODB_TABLE': dynamodb_table
    }
    
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
    
    logger.info("Starting CSV to Kafka processor with metrics")
    logger.info(f"S3 Source: s3://{s3_bucket}/{s3_key}")
    logger.info(f"Kafka Topic: {kafka_topic}")
    logger.info(f"Job ID: {job_id}")
    logger.info(f"Metrics Enabled: {enable_metrics}")
    
    # Initialize checkpoint manager
    checkpoint_manager = CheckpointManager(dynamodb_table, job_id)
    
    # Initialize metrics emitter
    metrics_emitter = None
    if enable_metrics:
        metrics_emitter = MetricsEmitter(namespace='CSVToKafka', job_id=job_id)
        logger.info("CloudWatch metrics enabled")
    
    # Initialize and run processor
    processor = CSVToKafkaProcessor(
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        kafka_bootstrap_servers=kafka_bootstrap_servers,
        kafka_topic=kafka_topic,
        checkpoint_manager=checkpoint_manager,
        metrics_emitter=metrics_emitter
    )
    
    try:
        processor.process()
        logger.info("Processing completed successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
