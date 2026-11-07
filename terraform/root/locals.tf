# reusable names and tags save typing values every time
locals {
  name_prefix = "${var.project_name}-${var.environment}"

  lambda_function_names = {
    poller    = "${local.name_prefix}-poller"
    processor = "${local.name_prefix}-processor"
    read      = "${local.name_prefix}-read"
  }

  # Four eBird attempts, backoff, and AWS calls per sequentially polled region.
  poller_timeout_seconds = min(900, 300 * length(var.ebird_regions))

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
