output "role_arn" {
  description = "ARN of the read Lambda IAM role."
  value       = aws_iam_role.read.arn
}
