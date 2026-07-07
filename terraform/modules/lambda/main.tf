# creates the poller function in lambda
resource "aws_lambda_function" "poller_function" {
  function_name = var.function_name

  filename         = var.filename
  source_code_hash = filebase64sha256(var.filename)

  role    = var.role_arn
  handler = var.handler
  runtime = var.runtime

  timeout     = 30
  memory_size = 256
}
