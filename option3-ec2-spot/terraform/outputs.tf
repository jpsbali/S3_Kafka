output "launch_template_id" {
  description = "Launch template ID"
  value       = aws_launch_template.spot.id
}

output "dynamodb_checkpoint_table" {
  description = "DynamoDB checkpoint table name"
  value       = aws_dynamodb_table.checkpoint.name
}

output "iam_instance_profile" {
  description = "IAM instance profile name"
  value       = aws_iam_instance_profile.ec2_profile.name
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.ec2_sg.id
}
