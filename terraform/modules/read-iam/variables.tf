variable "role_name" {
  description = "Name of the read Lambda IAM role."
  type        = string
}

variable "log_group_arn" {
  description = "ARN of the Terraform-managed log group this function may write to."
  type        = string
}

variable "sightings_table_arn" {
  description = "ARN of the processed sightings table the read function may query."
  type        = string
}
