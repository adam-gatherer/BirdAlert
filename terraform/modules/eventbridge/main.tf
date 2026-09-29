resource "aws_cloudwatch_event_rule" "poller" {
  name                = var.rule_name
  description         = "Invokes the BirdAlert poller every 15 minutes."
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "poller" {
  rule = aws_cloudwatch_event_rule.poller.name
  arn  = var.lambda_function_arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.poller.arn
}
