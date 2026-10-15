output "endpoint" {
  description = "Base URL of the public read API."
  value       = aws_apigatewayv2_api.read.api_endpoint
}

output "api_id" {
  description = "ID of the HTTP API used for CloudWatch monitoring."
  value       = aws_apigatewayv2_api.read.id
}
