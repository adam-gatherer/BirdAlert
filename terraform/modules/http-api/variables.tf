variable "api_name" {
  description = "Name of the HTTP API."
  type        = string
}

variable "lambda_function_arn" {
  description = "ARN of the Lambda function serving API requests."
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the Lambda function serving API requests."
  type        = string
}

variable "allowed_origins" {
  description = "Browser origins permitted by the API CORS response."
  type        = list(string)
}

variable "sightings_throttle_rate" {
  description = "Sustained requests per second allowed for GET /sightings."
  type        = number
}

variable "sightings_throttle_burst" {
  description = "Burst requests allowed for GET /sightings."
  type        = number
}

variable "health_throttle_rate" {
  description = "Sustained requests per second allowed for GET /health."
  type        = number
}

variable "health_throttle_burst" {
  description = "Burst requests allowed for GET /health."
  type        = number
}
