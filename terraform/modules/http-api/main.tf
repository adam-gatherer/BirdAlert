resource "aws_apigatewayv2_api" "read" {
  name          = var.api_name
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["content-type"]
    allow_methods = ["GET"]
    allow_origins = var.allowed_origins
  }
}

resource "aws_apigatewayv2_integration" "read" {
  api_id                 = aws_apigatewayv2_api.read.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_function_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "sightings" {
  api_id    = aws_apigatewayv2_api.read.id
  route_key = "GET /sightings"
  target    = "integrations/${aws_apigatewayv2_integration.read.id}"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.read.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.read.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.read.id
  name        = "$default"
  auto_deploy = true

  route_settings {
    route_key              = aws_apigatewayv2_route.sightings.route_key
    throttling_rate_limit  = var.sightings_throttle_rate
    throttling_burst_limit = var.sightings_throttle_burst
  }

  route_settings {
    route_key              = aws_apigatewayv2_route.health.route_key
    throttling_rate_limit  = var.health_throttle_rate
    throttling_burst_limit = var.health_throttle_burst
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.read.execution_arn}/*/*"
}
