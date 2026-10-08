output "role_arn" {
  description = "ARN of the processor Lambda IAM role."
  value       = aws_iam_role.processor.arn
}
