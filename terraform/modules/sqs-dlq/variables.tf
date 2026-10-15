variable "queue_name" {
  description = "Name of the dead-letter queue."
  type        = string
}

variable "message_retention_seconds" {
  description = "How long failed events remain available for investigation."
  type        = number
  default     = 1209600

  validation {
    condition     = var.message_retention_seconds >= 60 && var.message_retention_seconds <= 1209600
    error_message = "message_retention_seconds must be between 60 seconds and 14 days."
  }
}
