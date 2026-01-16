# Enhancement Plan: Metrics Dashboard

## Overview

Add a real-time metrics dashboard for monitoring CSV to Kafka processing with:
- Real-time throughput monitoring
- Progress visualization
- Cost tracking

**Estimated Effort:** 2-3 days  
**Complexity:** Medium  
**Dependencies:** AWS CloudWatch, Lambda, API Gateway (optional: Grafana/QuickSight)

---

## Architecture Options

### Option A: CloudWatch Dashboard (Recommended - Simplest)
**Pros:** Native AWS, no additional infrastructure, free tier available  
**Cons:** Limited customization, AWS Console only

### Option B: Grafana on ECS (Most Flexible)
**Pros:** Beautiful dashboards, highly customizable, open source  
**Cons:** Additional infrastructure cost (~$10-20/month)

### Option C: AWS QuickSight (Business Intelligence)
**Pros:** Advanced analytics, sharing capabilities  
**Cons:** Higher cost ($9/user/month), overkill for simple monitoring

**Recommendation:** Start with Option A (CloudWatch), migrate to Option B if needed.

---

## Implementation Plan

### Phase 1: Emit Custom Metrics (1 day)

#### 1.1 Modify processor.py to Emit CloudWatch Metrics

**Location:** `option*/app/processor.py`

**Changes needed:**
```python
import boto3
from datetime import datetime

class MetricsEmitter:
    def __init__(self, namespace='CSVToKafka', job_id='csv-job-1'):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
        self.job_id = job_id
    
    def emit_throughput(self, records_per_second):
        """Emit throughput metric"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': 'RecordsPerSecond',
                'Value': records_per_second,
                'Unit': 'Count/Second',
                'Dimensions': [{'Name': 'JobId', 'Value': self.job_id}]
            }]
        )
    
    def emit_progress(self, current_line, total_lines):
        """Emit progress percentage"""
        percentage = (current_line / total_lines) * 100
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': 'ProgressPercentage',
                'Value': percentage,
                'Unit': 'Percent',
                'Dimensions': [{'Name': 'JobId', 'Value': self.job_id}]
            }]
        )

    
    def emit_kafka_latency(self, latency_ms):
        """Emit Kafka send latency"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': 'KafkaLatency',
                'Value': latency_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [{'Name': 'JobId', 'Value': self.job_id}]
            }]
        )
    
    def emit_error_count(self, error_count):
        """Emit error count"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': 'ErrorCount',
                'Value': error_count,
                'Unit': 'Count',
                'Dimensions': [{'Name': 'JobId', 'Value': self.job_id}]
            }]
        )
```

**Integration into CSVToKafkaProcessor:**
```python
class CSVToKafkaProcessor:
    def __init__(self, ..., total_lines=None):
        # ... existing code ...
        self.metrics = MetricsEmitter(job_id=job_id)
        self.total_lines = total_lines
        self.start_time = time.time()
        self.last_metric_time = time.time()
        self.records_since_last_metric = 0
    
    def process(self):
        # ... existing code ...
        for row in csv_reader:
            current_line += 1
            
            # Send to Kafka
            start = time.time()
            success = self._send_to_kafka(row, current_line)
            latency = (time.time() - start) * 1000
            
            if success:
                records_sent += 1
                self.records_since_last_metric += 1
                
                # Emit latency
                self.metrics.emit_kafka_latency(latency)
                
                # Emit throughput every 1000 records
                if records_sent % 1000 == 0:
                    elapsed = time.time() - self.last_metric_time
                    throughput = self.records_since_last_metric / elapsed
                    self.metrics.emit_throughput(throughput)
                    self.last_metric_time = time.time()
                    self.records_since_last_metric = 0
                
                # Emit progress every 10000 records
                if records_sent % 10000 == 0:
                    if self.total_lines:
                        self.metrics.emit_progress(current_line, self.total_lines)
```

**IAM Permissions needed:**
Add to task role policy:
```json
{
  "Effect": "Allow",
  "Action": [
    "cloudwatch:PutMetricData"
  ],
  "Resource": "*"
}
```

---

### Phase 2: Create CloudWatch Dashboard (2 hours)

#### 2.1 Dashboard Configuration

Create CloudWatch Dashboard with these widgets:

**Widget 1: Real-Time Throughput**
- Metric: `CSVToKafka/RecordsPerSecond`
- Type: Line graph
- Period: 1 minute
- Statistic: Average

**Widget 2: Progress Gauge**
- Metric: `CSVToKafka/ProgressPercentage`
- Type: Number
- Period: 1 minute
- Statistic: Maximum

**Widget 3: Kafka Latency**
- Metric: `CSVToKafka/KafkaLatency`
- Type: Line graph
- Period: 1 minute
- Statistics: Average, p99

**Widget 4: Error Count**
- Metric: `CSVToKafka/ErrorCount`
- Type: Number
- Period: 5 minutes
- Statistic: Sum

**Widget 5: Records Processed**
- Source: DynamoDB checkpoint table
- Type: Number (via CloudWatch Logs Insights)

**Widget 6: Estimated Time Remaining**
- Calculated metric based on throughput and remaining records

#### 2.2 Terraform Code for Dashboard

**New file:** `option*/terraform/cloudwatch_dashboard.tf`

```hcl
resource "aws_cloudwatch_dashboard" "csv_kafka" {
  dashboard_name = "csv-to-kafka-metrics"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["CSVToKafka", "RecordsPerSecond", { stat = "Average" }]
          ]
          period = 60
          stat = "Average"
          region = var.aws_region
          title = "Throughput (Records/Second)"
          yAxis = { left = { min = 0 } }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["CSVToKafka", "ProgressPercentage", { stat = "Maximum" }]
          ]
          period = 60
          stat = "Maximum"
          region = var.aws_region
          title = "Progress (%)"
          yAxis = { left = { min = 0, max = 100 } }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["CSVToKafka", "KafkaLatency", { stat = "Average", label = "Avg" }],
            ["...", { stat = "p99", label = "p99" }]
          ]
          period = 60
          region = var.aws_region
          title = "Kafka Send Latency (ms)"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["CSVToKafka", "ErrorCount", { stat = "Sum" }]
          ]
          period = 300
          stat = "Sum"
          region = var.aws_region
          title = "Errors (Last 5 min)"
        }
      }
    ]
  })
}

output "dashboard_url" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.csv_kafka.dashboard_name}"
}
```

---

### Phase 3: Cost Tracking (4 hours)

#### 3.1 Cost Calculation Lambda

**New file:** `cost-tracker/lambda_function.py`

```python
import boto3
import json
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')
ce = boto3.client('ce')  # Cost Explorer

def calculate_costs(job_id, start_time, end_time):
    """Calculate costs for a job run"""
    
    # Get cost from Cost Explorer
    response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': start_time.strftime('%Y-%m-%d'),
            'End': end_time.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',
        Metrics=['UnblendedCost'],
        Filter={
            'Tags': {
                'Key': 'JobId',
                'Values': [job_id]
            }
        }
    )
    
    total_cost = sum(
        float(result['Total']['UnblendedCost']['Amount'])
        for result in response['ResultsByTime']
    )
    
    return total_cost

def lambda_handler(event, context):
    """Track costs for running jobs"""
    
    table = dynamodb.Table('csv-kafka-checkpoint')
    
    # Scan for active jobs
    response = table.scan(
        FilterExpression='attribute_exists(timestamp) AND attribute_not_exists(#status)',
        ExpressionAttributeNames={'#status': 'status'}
    )
    
    for item in response['Items']:
        job_id = item['job_id']
        start_time = datetime.fromtimestamp(item['timestamp'])
        
        # Calculate estimated cost
        elapsed_hours = (datetime.now() - start_time).total_seconds() / 3600
        
        # Estimate based on compute type (from tags or config)
        # ECS Fargate: $0.04048/hour for 2vCPU, 4GB
        # AWS Batch Spot: ~$0.012/hour
        # EC2 Spot: ~$0.012/hour
        
        estimated_cost = elapsed_hours * 0.04  # Adjust based on option
        
        # Emit cost metric
        cloudwatch.put_metric_data(
            Namespace='CSVToKafka',
            MetricData=[{
                'MetricName': 'EstimatedCost',
                'Value': estimated_cost,
                'Unit': 'None',
                'Dimensions': [{'Name': 'JobId', 'Value': job_id}]
            }]
        )
    
    return {'statusCode': 200}
```

#### 3.2 EventBridge Rule for Cost Tracking

**Terraform code:**
```hcl
resource "aws_lambda_function" "cost_tracker" {
  filename      = "cost-tracker.zip"
  function_name = "csv-kafka-cost-tracker"
  role          = aws_iam_role.cost_tracker_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.11"
}

resource "aws_cloudwatch_event_rule" "cost_tracking" {
  name                = "csv-kafka-cost-tracking"
  description         = "Track costs every 5 minutes"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "cost_tracker" {
  rule      = aws_cloudwatch_event_rule.cost_tracking.name
  target_id = "CostTracker"
  arn       = aws_lambda_function.cost_tracker.arn
}
```

#### 3.3 Cost Dashboard Widget

Add to CloudWatch Dashboard:
```json
{
  "type": "metric",
  "properties": {
    "metrics": [
      ["CSVToKafka", "EstimatedCost", { "stat": "Maximum" }]
    ],
    "period": 300,
    "stat": "Maximum",
    "region": "us-east-1",
    "title": "Estimated Cost ($)",
    "yAxis": { "left": { "min": 0 } }
  }
}
```

---

### Phase 4: Enhanced Progress Tracking (2 hours)

#### 4.1 Add Total Lines Detection

Modify processor to detect total lines:

```python
def get_total_lines(s3_client, bucket, key):
    """Get total lines in CSV (cached in DynamoDB)"""
    # Check cache first
    table = boto3.resource('dynamodb').Table('csv-kafka-checkpoint')
    cache_key = f"{bucket}/{key}"
    
    try:
        response = table.get_item(Key={'job_id': f'linecount-{cache_key}'})
        if 'Item' in response:
            return int(response['Item']['total_lines'])
    except:
        pass
    
    # Count lines (expensive, do once)
    logger.info("Counting total lines in CSV...")
    total = 0
    with smart_open(f's3://{bucket}/{key}', 'r', transport_params={'client': s3_client}) as f:
        for _ in f:
            total += 1
    
    # Cache result
    table.put_item(Item={
        'job_id': f'linecount-{cache_key}',
        'total_lines': total,
        'timestamp': int(time.time())
    })
    
    return total
```

#### 4.2 Add ETA Calculation

```python
def calculate_eta(current_line, total_lines, start_time):
    """Calculate estimated time to completion"""
    elapsed = time.time() - start_time
    rate = current_line / elapsed
    remaining = total_lines - current_line
    eta_seconds = remaining / rate if rate > 0 else 0
    return eta_seconds

# In process() method:
if records_sent % 10000 == 0:
    eta = calculate_eta(current_line, self.total_lines, self.start_time)
    self.metrics.emit_eta(eta)
```

---

## Implementation Steps

### Step 1: Update Application Code (Day 1)

1. **Add MetricsEmitter class** to `processor.py`
2. **Integrate metrics** into CSVToKafkaProcessor
3. **Add total lines detection**
4. **Add ETA calculation**
5. **Update requirements.txt** (no new dependencies needed)
6. **Test locally** with small CSV

### Step 2: Update Infrastructure (Day 1)

1. **Add CloudWatch permissions** to IAM role
2. **Create cloudwatch_dashboard.tf**
3. **Add resource tags** for cost tracking
4. **Deploy with Terraform**

### Step 3: Create Cost Tracker (Day 2)

1. **Create Lambda function** for cost tracking
2. **Create EventBridge rule**
3. **Add IAM permissions** for Cost Explorer
4. **Deploy Lambda**
5. **Test cost calculations**

### Step 4: Build Dashboard (Day 2)

1. **Create CloudWatch Dashboard** via Terraform
2. **Add all widgets** (throughput, progress, latency, errors, cost)
3. **Test with running job**
4. **Document dashboard URL**

### Step 5: Testing & Documentation (Day 3)

1. **Run test job** with 1M rows
2. **Verify all metrics** appear
3. **Verify cost tracking** works
4. **Update documentation**
5. **Create dashboard screenshots**

---

## File Changes Required

### New Files
```
cost-tracker/
├── lambda_function.py          # Cost tracking Lambda
├── requirements.txt            # Lambda dependencies
└── README.md                   # Cost tracker docs

option*/terraform/
└── cloudwatch_dashboard.tf     # Dashboard infrastructure

docs/
└── DASHBOARD_GUIDE.md          # Dashboard usage guide
```

### Modified Files
```
option1-ecs-fargate/app/processor.py    # Add metrics
option2-aws-batch/app/processor.py      # Add metrics
option1-ecs-fargate/terraform/main.tf   # Add CloudWatch permissions
option2-aws-batch/terraform/main.tf     # Add CloudWatch permissions
```

---

## Metrics to Track

### Performance Metrics
- **RecordsPerSecond** - Throughput
- **KafkaLatency** - Send latency (avg, p99)
- **ProgressPercentage** - % complete
- **ETASeconds** - Estimated time remaining

### Operational Metrics
- **ErrorCount** - Errors in last 5 min
- **RetryCount** - Kafka retries
- **CheckpointCount** - Checkpoints saved

### Cost Metrics
- **EstimatedCost** - Running cost estimate
- **CostPerMillionRecords** - Cost efficiency

---

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────┐
│  CSV to Kafka Processing Dashboard                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Throughput      │  │  Progress        │            │
│  │  45,234 rec/sec  │  │  67.3%           │            │
│  │  [Line Graph]    │  │  [Gauge]         │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Kafka Latency   │  │  Errors          │            │
│  │  12ms avg        │  │  0 errors        │            │
│  │  [Line Graph]    │  │  [Number]        │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Records Done    │  │  ETA             │            │
│  │  67.3M / 100M    │  │  45 minutes      │            │
│  │  [Number]        │  │  [Number]        │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  ┌──────────────────────────────────────────┐          │
│  │  Estimated Cost: $0.23                    │          │
│  │  [Line Graph showing cost over time]      │          │
│  └──────────────────────────────────────────┘          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Cost Estimate for Dashboard

### CloudWatch Costs
- **Custom Metrics:** $0.30 per metric/month (first 10K metrics free)
- **Dashboard:** $3/month per dashboard
- **API Calls:** Minimal (included in free tier)

### Lambda Costs (Cost Tracker)
- **Invocations:** 8,640/month (every 5 min)
- **Cost:** ~$0.20/month (well within free tier)

**Total Additional Cost:** ~$3-5/month

---

## Alternative: Grafana Dashboard (Optional)

If CloudWatch Dashboard is insufficient:

### Setup Grafana on ECS
1. Deploy Grafana container on ECS
2. Configure CloudWatch data source
3. Import pre-built dashboard
4. Add authentication

**Cost:** ~$10-20/month for ECS task

**Benefits:**
- More beautiful visualizations
- Better customization
- Alerting capabilities
- Shareable dashboards

---

## Testing Plan

### Unit Tests
- Test MetricsEmitter methods
- Test ETA calculation
- Test cost calculation

### Integration Tests
- Run with 10K row CSV
- Verify metrics in CloudWatch
- Verify dashboard displays correctly
- Verify cost tracking works

### Load Tests
- Run with 1M row CSV
- Monitor metric emission rate
- Verify no performance impact
- Verify cost accuracy

---

## Documentation Updates

### New Documentation
- **DASHBOARD_GUIDE.md** - How to use dashboard
- **METRICS_REFERENCE.md** - Metric definitions
- **COST_TRACKING.md** - Cost tracking details

### Updated Documentation
- **OPERATIONS.md** - Add dashboard monitoring section
- **QUICK_REFERENCE.md** - Add dashboard URL
- **README.md** - Mention dashboard feature

---

## Success Criteria

✅ Real-time throughput visible in dashboard
✅ Progress percentage updates every minute
✅ Kafka latency tracked (avg and p99)
✅ Cost estimate updates every 5 minutes
✅ ETA calculation accurate within 10%
✅ Dashboard accessible via URL
✅ No performance impact on processing
✅ Documentation complete

---

## Rollout Plan

### Phase 1: Pilot (Week 1)
- Deploy to Option 1 (ECS Fargate) only
- Test with small jobs
- Gather feedback

### Phase 2: Expand (Week 2)
- Deploy to Option 2 (AWS Batch)
- Deploy to Option 3 (EC2 Spot)
- Refine metrics based on feedback

### Phase 3: Production (Week 3)
- Enable for all production jobs
- Train team on dashboard
- Document best practices

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Metric emission slows processing | High | Emit metrics asynchronously, batch metrics |
| CloudWatch costs too high | Medium | Use metric filters, reduce emission frequency |
| Dashboard not accessible | Low | Document URL, add to README |
| Cost tracking inaccurate | Medium | Use AWS Cost Explorer API, add buffer |

---

## Next Steps

1. **Review this plan** with team
2. **Approve budget** (~$5/month additional cost)
3. **Assign developer** (2-3 days effort)
4. **Create feature branch** `feature/metrics-dashboard`
5. **Implement Phase 1** (emit metrics)
6. **Test and iterate**
7. **Deploy to production**

---

**Estimated Timeline:** 2-3 days development + 1 week rollout  
**Estimated Cost:** $3-5/month ongoing  
**Complexity:** Medium  
**Value:** High (visibility into processing)

---

**Ready to implement? Start with Phase 1!**
