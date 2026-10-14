output "endpoint" {
  description = "Base URL of the public read API."
  value       = aws_apigatewayv2_api.read.api_endpoint
}
