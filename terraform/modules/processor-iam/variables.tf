variable "role_name" {
  description = "Name of the processor Lambda IAM role."
  type        = string
}

variable "bucket_arn" {
  description = "ARN of the raw S3 bucket the processor may read."
  type        = string
}

variable "sightings_table_arn" {
  description = "ARN of the DynamoDB table the processor may write."
  type        = string
}
