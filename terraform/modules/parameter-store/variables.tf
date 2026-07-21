variable "parameter_name" {
  description = "SSM parameter name."
  type        = string
}


variable "parameter_value" {
  description = "SSM parameter value"
  type        = string
  sensitive   = true
}
