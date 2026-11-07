# creates a Lambda function
resource "aws_lambda_function" "poller_function" {
  function_name = var.function_name

  filename         = var.filename
  source_code_hash = filebase64sha256(var.filename)

  role    = var.role_arn
  handler = var.handler
  runtime = var.runtime

  timeout     = var.timeout
  memory_size = var.memory_size

  dynamic "environment" {
    for_each = length(var.environment_variables) > 0 ? [1] : []

    content {
      variables = var.environment_variables
    }
  }
}
