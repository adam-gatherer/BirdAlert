variable "role_name" {
  description = "Name of the processor Lambda IAM role."
  type        = string
}

variable "log_group_arn" {
  description = "ARN of the Terraform-managed log group this function may write to."
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

variable "processor_dlq_arn" {
  description = "ARN of the processor failure destination queue."
  type        = string
}
