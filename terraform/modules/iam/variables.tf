variable "role_name" {
  description = "Name of the IAM role."
  type        = string
}

variable "log_group_arn" {
  description = "ARN of the Terraform-managed log group this function may write to."
  type        = string
}

variable "parameter_arn" {
  description = "ARN of the eBird API key parameter."
  type        = string
}

variable "bucket_arn" {
  description = "ARN of the raw bucket."
  type        = string
}

variable "poller_dlq_arn" {
  description = "ARN of the queue receiving exhausted poller executions."
  type        = string
}
