resource "aws_sqs_queue" "dlq" {
  name                      = var.queue_name
  message_retention_seconds = var.message_retention_seconds
  receive_wait_time_seconds = 20
  sqs_managed_sse_enabled   = true
}
