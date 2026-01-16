# Metrics Dashboard Guide

## Overview

The CSV to Kafka processor now includes real-time metrics monitoring through CloudWatch. This guide explains how to use the dashboard and interpret the metrics.

**Dashboard URL:** Available in Terraform outputs after deployment

---

## Accessing the Dashboard

### Via Terraform Output
```bash
cd option1-ecs-fargate/terraform  # or option2-aws-batch/terraform
terraform output dashboard_url
```

### Via AWS Console
1. Navigate to CloudWatch → Dashboards
2. Find dashboard named: `csv-to-kafka-metrics-{job_id}`
3. Click to open

---

## Dashboard Widgets

### Row 1: Performance Overview

#### 1. Throughput (Records/Second)
**What it shows:** Real-time processing speed

**Metrics:**
- Average records processed per second
- Updated every minute

**What to look for:**
- Steady throughput indicates healthy processing
- Drops may indicate Kafka issues or network problems
- Typical range: 10,000-50,000 records/sec

**Example:**
```
45,234 records/sec - Excellent performance
12,500 records/sec - Normal performance
< 1,000 records/sec - Investigate issues
```

#### 2. Progress (%)
**What it shows:** Completion percentage

**Metrics:**
- Percentage of total records processed
- Updated every minute

**What to look for:**
- Steady increase indicates normal progress
- Stalled progress indicates processing stopped
- 100% means job complete

**Example:**
```
67.3% - Job is 67% complete
100% - Job finished
```

---

### Row 2: Quality Metrics

#### 3. Kafka Send Latency (ms)
**What it shows:** Time to send each record to Kafka

**Metrics:**
- Average latency (typical)
- p99 latency (worst case)
- Updated every minute

**What to look for:**
- Low latency (< 50ms) is ideal
- High latency (> 500ms) may indicate Kafka issues
- Spikes in p99 show occasional slow sends

**Example:**
```
Avg: 12ms, p99: 45ms - Excellent
Avg: 150ms, p99: 800ms - Investigate Kafka
```

#### 4. Errors and Retries (Last 5 min)
**What it shows:** Error count and retry attempts

**Metrics:**
- Total errors in last 5 minutes
- Total retries in last 5 minutes

**What to look for:**
- Zero errors is ideal
- Retries without errors are normal (transient issues)
- Errors indicate serious problems

**Example:**
```
Errors: 0, Retries: 5 - Normal (transient issues handled)
Errors: 10, Retries: 50 - Investigate immediately
```

---

### Row 3: Progress Details

#### 5. Records Status
**What it shows:** Records processed vs remaining

**Metrics:**
- Records Processed (current count)
- Records Remaining (to process)

**What to look for:**
- Processed should increase steadily
- Remaining should decrease steadily
- Both should sum to total records

**Example:**
```
Processed: 67.3M
Remaining: 32.7M
Total: 100M
```

#### 6. Estimated Time Remaining
**What it shows:** ETA to completion

**Metrics:**
- Minutes until job completes
- Based on current throughput

**What to look for:**
- Decreasing ETA indicates normal progress
- Increasing ETA indicates slowdown
- Accurate within 10-15%

**Example:**
```
45 minutes - Job will complete in ~45 min
```

#### 7. Checkpoints Saved
**What it shows:** Number of checkpoints saved

**Metrics:**
- Total checkpoints in last 5 minutes
- One checkpoint every 10,000 records

**What to look for:**
- Regular checkpoints indicate healthy processing
- No checkpoints may indicate stalled job
- Typical: 1 checkpoint per minute at 10K records/sec

**Example:**
```
5 checkpoints - Normal (5 checkpoints in 5 min)
0 checkpoints - Job may be stalled
```

---

## Interpreting the Dashboard

### Healthy Processing
```
Throughput: 30,000-50,000 rec/sec (steady)
Progress: Increasing steadily
Latency: < 50ms average
Errors: 0
Retries: < 10 per 5 min
ETA: Decreasing
Checkpoints: Regular (every 1-2 min)
```

### Warning Signs
```
Throughput: Dropping or erratic
Progress: Stalled (not increasing)
Latency: > 200ms average
Errors: > 0
Retries: > 50 per 5 min
ETA: Increasing
Checkpoints: None for > 5 min
```

### Critical Issues
```
Throughput: < 1,000 rec/sec or zero
Progress: Not moving for > 10 min
Latency: > 1000ms
Errors: > 10
Retries: > 100 per 5 min
ETA: N/A or very high
Checkpoints: None for > 10 min
```

---

## Common Scenarios

### Scenario 1: Job Running Normally
**Dashboard shows:**
- Throughput: 40,000 rec/sec
- Progress: 45% and increasing
- Latency: 15ms avg, 35ms p99
- Errors: 0
- ETA: 30 minutes

**Action:** None - job is healthy

### Scenario 2: Kafka Slowdown
**Dashboard shows:**
- Throughput: Dropping from 40K to 10K
- Progress: Still increasing but slowly
- Latency: 250ms avg, 1200ms p99
- Errors: 0
- Retries: 20 per 5 min

**Action:** Check Kafka cluster health, broker CPU/memory

### Scenario 3: Job Stalled
**Dashboard shows:**
- Throughput: 0
- Progress: Stuck at 67%
- Latency: No data
- Errors: 5
- Checkpoints: None for 15 min

**Action:** Check CloudWatch logs, check last checkpoint in DynamoDB, restart job

### Scenario 4: Network Issues
**Dashboard shows:**
- Throughput: Erratic (spikes and drops)
- Progress: Increasing but inconsistent
- Latency: High variance (50ms to 500ms)
- Errors: 0
- Retries: 100+ per 5 min

**Action:** Check network connectivity, VPC flow logs, NAT gateway

---

## Metrics Reference

### All Available Metrics

| Metric Name | Unit | Description | Typical Value |
|-------------|------|-------------|---------------|
| RecordsPerSecond | Count/Second | Processing throughput | 10K-50K |
| ProgressPercentage | Percent | Completion percentage | 0-100 |
| RecordsProcessed | Count | Total records processed | 0-100M |
| RecordsRemaining | Count | Records left to process | 100M-0 |
| KafkaLatency | Milliseconds | Kafka send latency | 10-50ms |
| ErrorCount | Count | Total errors | 0 |
| RetryCount | Count | Total retries | 0-100 |
| ETASeconds | Seconds | Time to completion | 0-10800 |
| ETAMinutes | None | Time to completion (min) | 0-180 |
| CheckpointCount | Count | Checkpoints saved | 1 per 10K records |

---

## Alerting (Optional)

You can create CloudWatch Alarms based on these metrics:

### Recommended Alarms

**1. Low Throughput Alarm**
```
Metric: RecordsPerSecond
Condition: < 1000 for 5 minutes
Action: SNS notification
```

**2. High Error Rate Alarm**
```
Metric: ErrorCount
Condition: > 10 in 5 minutes
Action: SNS notification + stop job
```

**3. Job Stalled Alarm**
```
Metric: CheckpointCount
Condition: = 0 for 10 minutes
Action: SNS notification
```

**4. High Latency Alarm**
```
Metric: KafkaLatency (p99)
Condition: > 1000ms for 5 minutes
Action: SNS notification
```

### Creating Alarms via Terraform

Add to `cloudwatch_dashboard.tf`:
```hcl
resource "aws_cloudwatch_metric_alarm" "low_throughput" {
  alarm_name          = "csv-kafka-low-throughput"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "RecordsPerSecond"
  namespace           = "CSVToKafka"
  period              = "300"
  statistic           = "Average"
  threshold           = "1000"
  alarm_description   = "Alert when throughput drops below 1000 rec/sec"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

---

## Troubleshooting with Dashboard

### Problem: Dashboard shows no data
**Possible causes:**
- Metrics not enabled (check ENABLE_METRICS env var)
- Job not running
- Wrong job_id filter

**Solution:**
1. Check job is running: `aws ecs list-tasks --cluster csv-to-kafka-cluster`
2. Check metrics enabled in task definition
3. Wait 1-2 minutes for first metrics to appear

### Problem: Metrics stopped updating
**Possible causes:**
- Job crashed or stopped
- CloudWatch API issues
- Metrics buffer not flushing

**Solution:**
1. Check CloudWatch logs for errors
2. Check task/job status
3. Restart job if needed

### Problem: ETA is inaccurate
**Possible causes:**
- Throughput is variable
- Job just started (not enough data)
- Total lines not detected

**Solution:**
- ETA becomes more accurate after 10-15 minutes
- Check logs for "Total lines in CSV" message
- ETA is estimate only, actual time may vary

---

## Best Practices

1. **Monitor regularly** - Check dashboard every 15-30 minutes for long jobs
2. **Set up alarms** - Get notified of issues automatically
3. **Compare runs** - Track metrics across multiple jobs to identify trends
4. **Save screenshots** - Document performance for future reference
5. **Use job_id dimension** - Filter metrics by specific job
6. **Check logs too** - Dashboard shows metrics, logs show details

---

## Disabling Metrics

If you want to disable metrics (not recommended):

**Environment Variable:**
```bash
ENABLE_METRICS=false
```

**In Terraform:**
```hcl
environment = [
  {
    name  = "ENABLE_METRICS"
    value = "false"
  }
]
```

**Note:** Disabling metrics removes dashboard visibility but slightly improves performance.

---

## Cost

**CloudWatch Metrics Cost:**
- First 10,000 metrics: Free
- Additional metrics: $0.30 per metric/month
- Dashboard: $3/month

**Typical cost for this solution:**
- ~10 metrics emitted
- 1 dashboard
- **Total: ~$3/month**

**API calls:** Included in free tier (< 1M calls/month)

---

## Support

For issues with the dashboard:
1. Check [OPERATIONS.md](OPERATIONS.md) - Troubleshooting section
2. Verify IAM permissions include `cloudwatch:PutMetricData`
3. Check CloudWatch Logs for metric emission errors
4. Verify metrics appear in CloudWatch Metrics console

---

**Dashboard Version:** 1.0.0  
**Last Updated:** January 16, 2026
