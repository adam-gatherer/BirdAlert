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
