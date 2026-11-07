output "queue_arn" {
  description = "ARN of the dead-letter queue."
  value       = aws_sqs_queue.dlq.arn
}

output "queue_url" {
  description = "URL of the dead-letter queue."
  value       = aws_sqs_queue.dlq.url
}
