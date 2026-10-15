# debugging output
#output "role_name_debug" {
#  value = "${local.name_prefix}-poller-role"
#}
# Public base URL for GET /sightings and GET /health.
output "read_api_endpoint" {
  description = "Base URL of the public read API."
  value       = module.read_api.endpoint
}

output "site_url" {
  description = "Public HTTPS URL of the BirdAlert static site."
  value       = module.static_site.site_url
}

output "operational_alarms_topic_arn" {
  description = "SNS topic receiving high-priority operational alarms."
  value       = aws_sns_topic.operational_alarms.arn
}

output "poller_dlq_url" {
  description = "SQS URL for failed poller deliveries."
  value       = module.poller_dlq.queue_url
}

output "processor_dlq_url" {
  description = "SQS URL for failed processor deliveries."
  value       = module.processor_dlq.queue_url
}
