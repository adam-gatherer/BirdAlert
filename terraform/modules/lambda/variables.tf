variable "function_name" {
  description = "Lambda function name."
  type        = string
}

variable "role_arn" {
  description = "IAM role ARN."
  type        = string
}

variable "filename" {
  description = "Path to deployment package."
  type        = string
}

variable "handler" {
  description = "Lambda handler."
  type        = string
}

variable "runtime" {
  description = "Lambda runtime."
  type        = string
}

variable "bucket_name" {
  description = "Raw S3 bucket."
  type        = string
}
