output "rule_arn" {
  description = "ARN of the EventBridge rule."

  value = aws_cloudwatch_event_rule.poller.arn
}
