output "bucket_name" {
  description = "Name of the private S3 bucket holding the static site."
  value       = aws_s3_bucket.site.bucket
}

output "site_url" {
  description = "HTTPS URL of the public CloudFront site."
  value       = "https://${aws_cloudfront_distribution.site.domain_name}"
}
