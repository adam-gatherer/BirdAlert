variable "bucket_name" {
  description = "Globally unique name of the private S3 bucket holding site assets."
  type        = string
}

variable "distribution_name" {
  description = "Name used for the CloudFront distribution and origin access control."
  type        = string
}

variable "site_domain_name" {
  description = "Optional custom domain name served by CloudFront."
  type        = string
  default     = null
  nullable    = true
}

variable "acm_certificate_arn" {
  description = "Optional ACM certificate ARN for site_domain_name. CloudFront certificates must be in us-east-1."
  type        = string
  default     = null
  nullable    = true
}
