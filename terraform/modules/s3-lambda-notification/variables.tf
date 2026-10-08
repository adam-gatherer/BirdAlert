variable "bucket_name" {
  description = "Name of the S3 bucket producing notifications."
  type        = string
}

variable "bucket_arn" {
  description = "ARN of the S3 bucket producing notifications."
  type        = string
}

variable "lambda_function_arn" {
  description = "ARN of the Lambda function invoked for new objects."
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the Lambda function invoked for new objects."
  type        = string
}
