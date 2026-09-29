variable "bucket_name" {
  description = "Name of the S3 bucket."
  type        = string
}

variable "retention_days" {
  description = "Number of days to retain raw S3 object versions."
  type        = number
}
