# debugging output
#output "role_name_debug" {
#  value = "${local.name_prefix}-poller-role"
#}
# Public base URL for GET /sightings and GET /health.
output "read_api_endpoint" {
  description = "Base URL of the public read API."
  value       = module.read_api.endpoint
}

output "site_url" {
  description = "Public HTTPS URL of the BirdAlert static site."
  value       = module.static_site.site_url
}
