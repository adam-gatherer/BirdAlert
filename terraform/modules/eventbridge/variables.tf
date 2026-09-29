variable "rule_name" {
  description = "Name of the EventBridge rule."
  type        = string
}

variable "schedule_expression" {
  description = "EventBridge schedule expression for the poller."
  type        = string
}

variable "lambda_function_arn" {
  description = "ARN of the Lambda function to invoke."
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the Lambda function to permit EventBridge to invoke."
  type        = string
}
