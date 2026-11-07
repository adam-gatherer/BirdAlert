output "notification_id" {
  description = "ID of the raw bucket notification configuration."
  value       = aws_s3_bucket_notification.raw_object_created.id
}
