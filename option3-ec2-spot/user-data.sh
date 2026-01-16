#!/bin/bash
set -e

# User data script for EC2 Spot instance
# This script runs on instance launch and processes the CSV

# Configuration - Replace these values
S3_BUCKET="your-bucket-name"
S3_KEY="path/to/your/file.csv"
KAFKA_BOOTSTRAP_SERVERS="b-1.your-msk.kafka.us-east-1.amazonaws.com:9092"
KAFKA_TOPIC="your-topic-name"
DYNAMODB_TABLE="csv-kafka-checkpoint-ec2"
JOB_ID="csv-job-1"
AWS_REGION="us-east-1"

# Install dependencies
yum update -y
yum install -y python3 python3-pip

# Install Python packages
pip3 install boto3 kafka-python smart-open[s3]

# Create processor script
cat > /home/ec2-user/processor.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
import os
import sys
import csv
import json
import time
import logging
import boto3
from kafka import KafkaProducer
from kafka.errors import KafkaError
from smart_open import open as smart_open
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CheckpointManager:
    def __init__(self, table_name, job_id):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self.job_id = job_id
    
    def get_last_processed_line(self):
        try:
            response = self.table.get_item(Key={'job_id': self.job_id})
            return int(response.get('Item', {}).get('last_line', 0))
        except:
            return 0
    
    def update_checkpoint(self, line_number, total_sent):
        self.table.put_item(Item={
            'job_id': self.job_id,
            'last_line': line_number,
            'total_sent': total_sent,
            'timestamp': int(time.time())
        })
    
    def mark_complete(self, total_lines):
        self.table.put_item(Item={
            'job_id': self.job_id,
            'last_line': total_lines,
            'total_sent': total_lines,
            'status': 'COMPLETED',
            'timestamp': int(time.time())
        })


def process_csv():
    s3_bucket = os.environ['S3_BUCKET']
    s3_key = os.environ['S3_KEY']
    kafka_servers = os.environ['KAFKA_BOOTSTRAP_SERVERS']
    kafka_topic = os.environ['KAFKA_TOPIC']
    dynamodb_table = os.environ['DYNAMODB_TABLE']
    job_id = os.environ['JOB_ID']
    
    checkpoint_mgr = CheckpointManager(dynamodb_table, job_id)
    start_line = checkpoint_mgr.get_last_processed_line()
    
    producer = KafkaProducer(
        bootstrap_servers=kafka_servers.split(','),
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        max_in_flight_requests_per_connection=1,
        acks='all',
        retries=2147483647,
        enable_idempotence=True
    )
    
    s3_uri = f's3://{s3_bucket}/{s3_key}'
    current_line = 0
    records_sent = 0
    
    try:
        with smart_open(s3_uri, 'r', transport_params={'client': boto3.client('s3')}) as f:
            reader = csv.DictReader(f)
            for row in reader:
                current_line += 1
                if current_line <= start_line:
                    continue
                
                future = producer.send(kafka_topic, value=row, partition=0)
                future.get(timeout=30)
                records_sent += 1
                
                if records_sent % 10000 == 0:
                    producer.flush()
                    checkpoint_mgr.update_checkpoint(current_line, records_sent)
                    logger.info(f"Progress: {records_sent} records")
        
        producer.flush()
        checkpoint_mgr.mark_complete(current_line)
        logger.info(f"COMPLETED: {records_sent} records")
    finally:
        producer.close()

if __name__ == '__main__':
    process_csv()
PYTHON_SCRIPT

# Set environment variables and run
export S3_BUCKET="$S3_BUCKET"
export S3_KEY="$S3_KEY"
export KAFKA_BOOTSTRAP_SERVERS="$KAFKA_BOOTSTRAP_SERVERS"
export KAFKA_TOPIC="$KAFKA_TOPIC"
export DYNAMODB_TABLE="$DYNAMODB_TABLE"
export JOB_ID="$JOB_ID"
export AWS_DEFAULT_REGION="$AWS_REGION"

# Run processor
python3 /home/ec2-user/processor.py > /var/log/csv-processor.log 2>&1

# Shutdown instance when complete
shutdown -h now
