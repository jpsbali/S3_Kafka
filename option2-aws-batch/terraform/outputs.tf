output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.app.repository_url
}

output "batch_job_queue" {
  description = "Batch job queue name"
  value       = aws_batch_job_queue.main.name
}

output "batch_job_definition" {
  description = "Batch job definition name"
  value       = aws_batch_job_definition.main.name
}

output "dynamodb_checkpoint_table" {
  description = "DynamoDB checkpoint table name"
  value       = aws_dynamodb_table.checkpoint.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.batch_logs.name
}
