output "table_arn" {
  description = "ARN of the processed sightings table."
  value       = aws_dynamodb_table.sightings.arn
}

output "table_name" {
  description = "Name of the processed sightings table."
  value       = aws_dynamodb_table.sightings.name
}
