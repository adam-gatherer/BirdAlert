variable "aws_region" {
  description = "AWS region for deployment."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "project_name" {
  description = "Project name."
  type        = string
}

variable "ebird_regions" {
  description = "eBird region codes to poll in this deployment."
  type        = list(string)

  validation {
    condition     = length(var.ebird_regions) > 0 && alltrue([for region in var.ebird_regions : trimspace(region) != ""])
    error_message = "ebird_regions must contain at least one non-empty region code."
  }

  validation {
    condition     = length(distinct(var.ebird_regions)) == length(var.ebird_regions)
    error_message = "ebird_regions must not contain duplicate region codes."
  }
}

variable "raw_retention_days" {
  description = "Number of days to retain raw S3 object versions."
  type        = number

  validation {
    condition     = var.raw_retention_days >= 1 && floor(var.raw_retention_days) == var.raw_retention_days
    error_message = "raw_retention_days must be a whole number of at least one day."
  }
}

variable "ebird_api_key" {
  description = "eBird API key."
  type        = string
  sensitive   = true
}

variable "sightings_throttle_rate" {
  description = "Sustained requests per second for GET /sightings."
  type        = number
  default     = 2

  validation {
    condition     = var.sightings_throttle_rate > 0
    error_message = "sightings_throttle_rate must be greater than zero."
  }
}

variable "sightings_throttle_burst" {
  description = "Burst requests allowed for GET /sightings."
  type        = number
  default     = 5

  validation {
    condition     = var.sightings_throttle_burst >= 1 && floor(var.sightings_throttle_burst) == var.sightings_throttle_burst
    error_message = "sightings_throttle_burst must be a whole number of at least one."
  }
}

variable "health_throttle_rate" {
  description = "Sustained requests per second for GET /health."
  type        = number
  default     = 1

  validation {
    condition     = var.health_throttle_rate > 0
    error_message = "health_throttle_rate must be greater than zero."
  }
}

variable "health_throttle_burst" {
  description = "Burst requests allowed for GET /health."
  type        = number
  default     = 2

  validation {
    condition     = var.health_throttle_burst >= 1 && floor(var.health_throttle_burst) == var.health_throttle_burst
    error_message = "health_throttle_burst must be a whole number of at least one."
  }
}

variable "alarm_email" {
  description = "Optional administrator email address subscribed to operational alarms."
  type        = string
  default     = null
  nullable    = true
}

variable "site_domain_name" {
  description = "Optional public custom domain for the CloudFront site, without a trailing dot."
  type        = string
  default     = null
  nullable    = true
}

variable "route53_zone_id" {
  description = "Route 53 public hosted-zone ID used for custom-domain records and ACM DNS validation."
  type        = string
  default     = null
  nullable    = true
}
