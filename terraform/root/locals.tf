# reusable names and tags save typing values every time
locals {
  name_prefix = "${var.project_name}-${var.environment}"

  site_directory   = "${path.module}/../../site"
  site_asset_files = toset([for file in fileset("${path.module}/../../site", "**") : file if file != "config.js.tftpl"])
  site_content_types = {
    css  = "text/css; charset=utf-8"
    html = "text/html; charset=utf-8"
    js   = "application/javascript; charset=utf-8"
  }

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
