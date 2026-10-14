variable "bucket_name" {
  description = "Globally unique name of the private S3 bucket holding site assets."
  type        = string
}

variable "distribution_name" {
  description = "Name used for the CloudFront distribution and origin access control."
  type        = string
}
