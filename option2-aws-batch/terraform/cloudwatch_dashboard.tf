# CloudWatch Dashboard for CSV to Kafka Metrics

resource "aws_cloudwatch_dashboard" "csv_kafka" {
  dashboard_name = "csv-to-kafka-metrics-${var.job_id}"

  dashboard_body = jsonencode({
    widgets = [
      # Row 1: Throughput and Progress
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["CSVToKafka", "RecordsPerSecond", { stat = "Average", label = "Throughput" }]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "Throughput (Records/Second)"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["CSVToKafka", "ProgressPercentage", { stat = "Maximum", label = "Progress %" }]
          ]
          period = 60
          stat   = "Maximum"
          region = var.aws_region
          title  = "Progress (%)"
          yAxis = {
            left = { min = 0, max = 100 }
          }
        }
      },
      # Row 2: Kafka Latency and Errors
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["CSVToKafka", "KafkaLatency", { stat = "Average", label = "Avg Latency" }],
            ["...", { stat = "p99", label = "p99 Latency" }]
          ]
          period = 60
          region = var.aws_region
          title  = "Kafka Send Latency (ms)"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["CSVToKafka", "ErrorCount", { stat = "Sum", label = "Errors" }],
            [".", "RetryCount", { stat = "Sum", label = "Retries" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Errors and Retries (Last 5 min)"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      # Row 3: Records Processed and ETA
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["CSVToKafka", "RecordsProcessed", { stat = "Maximum", label = "Processed" }],
            [".", "RecordsRemaining", { stat = "Maximum", label = "Remaining" }]
          ]
          period = 60
          stat   = "Maximum"
          region = var.aws_region
          title  = "Records Status"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 12
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["CSVToKafka", "ETAMinutes", { stat = "Maximum", label = "ETA (minutes)" }]
          ]
          period = 60
          stat   = "Maximum"
          region = var.aws_region
          title  = "Estimated Time Remaining"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 12
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["CSVToKafka", "CheckpointCount", { stat = "Sum", label = "Checkpoints" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Checkpoints Saved"
          yAxis = {
            left = { min = 0 }
          }
        }
      }
    ]
  })

  tags = {
    Name        = "CSV to Kafka Metrics Dashboard"
    Environment = "production"
    ManagedBy   = "Terraform"
  }
}

output "dashboard_url" {
  description = "CloudWatch Dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.csv_kafka.dashboard_name}"
}
