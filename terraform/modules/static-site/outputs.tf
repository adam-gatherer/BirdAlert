output "bucket_name" {
  description = "Name of the private S3 bucket holding the static site."
  value       = aws_s3_bucket.site.bucket
}

output "site_url" {
  description = "HTTPS URL of the public CloudFront site."
  value       = "https://${coalesce(var.site_domain_name, aws_cloudfront_distribution.site.domain_name)}"
}

output "distribution_domain_name" {
  description = "CloudFront distribution domain name used by Route 53 alias records."
  value       = aws_cloudfront_distribution.site.domain_name
}

output "distribution_hosted_zone_id" {
  description = "CloudFront hosted-zone ID used by Route 53 alias records."
  value       = aws_cloudfront_distribution.site.hosted_zone_id
}
