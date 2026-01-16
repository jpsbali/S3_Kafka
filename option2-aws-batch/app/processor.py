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
