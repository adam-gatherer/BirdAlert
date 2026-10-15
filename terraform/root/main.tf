# Stable eight-character suffix prevents global S3 naming collisions.
resource "random_id" "raw_bucket_suffix" {
  byte_length = 4
}

resource "random_id" "site_bucket_suffix" {
  byte_length = 4
}

# creates the raw bucket for dumping API data
module "raw_bucket" {
  source = "../modules/s3"

  bucket_name    = "${local.name_prefix}-raw-${random_id.raw_bucket_suffix.hex}"
  retention_days = var.raw_retention_days
}

# creates the poller lambda function using the zipped app.py in /build
module "poller_lambda" {
  source = "../modules/lambda"

  depends_on = [aws_cloudwatch_log_group.lambda["poller"]]

  function_name = local.lambda_function_names.poller

  role_arn = module.poller_iam.role_arn

  filename = "../../build/poller.zip"

  handler = "app.lambda_handler"

  runtime = "python3.13"

  environment_variables = {
    RAW_BUCKET     = module.raw_bucket.bucket_name
    PARAMETER_NAME = module.ebird_api_key.parameter_name
    EBIRD_REGIONS  = join(",", var.ebird_regions)
  }
}

module "poller_dlq" {
  source = "../modules/sqs-dlq"

  queue_name = "${local.name_prefix}-poller-dlq"
}

# creates the parameter store loaded with our API key
module "ebird_api_key" {
  source = "../modules/parameter-store"

  parameter_name  = "/birdalert/${var.environment}/ebird/api-key"
  parameter_value = var.ebird_api_key
}

# creates IAM role and policies required by poller lambda function,
# adds api key from parameter store
module "poller_iam" {
  source = "../modules/iam"

  role_name = "${local.name_prefix}-poller-role"

  parameter_arn = module.ebird_api_key.parameter_arn

  bucket_arn = module.raw_bucket.bucket_arn
}

module "poller_schedule" {
  source = "../modules/eventbridge"

  rule_name             = "${local.name_prefix}-poller-schedule"
  schedule_expression   = "rate(15 minutes)"
  lambda_function_arn   = module.poller_lambda.function_arn
  lambda_function_name  = module.poller_lambda.function_name
  dead_letter_queue_arn = module.poller_dlq.queue_arn
}

data "aws_iam_policy_document" "poller_dlq" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions   = ["sqs:SendMessage"]
    resources = [module.poller_dlq.queue_arn]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [module.poller_schedule.rule_arn]
    }
  }
}

resource "aws_sqs_queue_policy" "poller_dlq" {
  queue_url = module.poller_dlq.queue_url
  policy    = data.aws_iam_policy_document.poller_dlq.json
}

# processes each raw response after it lands in S3
module "processor_lambda" {
  source = "../modules/lambda"

  depends_on = [aws_cloudwatch_log_group.lambda["processor"]]

  function_name = local.lambda_function_names.processor
  role_arn      = module.processor_iam.role_arn
  filename      = "../../build/processor.zip"
  handler       = "app.lambda_handler"
  runtime       = "python3.13"
  timeout       = 180

  environment_variables = {
    SIGHTINGS_TABLE = module.sightings_table.table_name
  }
}

module "processor_dlq" {
  source = "../modules/sqs-dlq"

  queue_name = "${local.name_prefix}-processor-dlq"
}

module "sightings_table" {
  source = "../modules/dynamodb"

  table_name = "${local.name_prefix}-sightings"
}

module "processor_iam" {
  source = "../modules/processor-iam"

  role_name           = "${local.name_prefix}-processor-role"
  bucket_arn          = module.raw_bucket.bucket_arn
  sightings_table_arn = module.sightings_table.table_arn
  processor_dlq_arn   = module.processor_dlq.queue_arn
}

resource "aws_lambda_function_event_invoke_config" "processor" {
  function_name                = module.processor_lambda.function_name
  maximum_retry_attempts       = 2
  maximum_event_age_in_seconds = 3600

  destination_config {
    on_failure {
      destination = module.processor_dlq.queue_arn
    }
  }
}

# Serves bounded public read requests from DynamoDB; it never reads raw S3 data.
module "read_lambda" {
  source = "../modules/lambda"

  depends_on = [aws_cloudwatch_log_group.lambda["read"]]

  function_name = local.lambda_function_names.read
  role_arn      = module.read_iam.role_arn
  filename      = "../../build/read.zip"
  handler       = "app.lambda_handler"
  runtime       = "python3.13"

  environment_variables = {
    SIGHTINGS_TABLE = module.sightings_table.table_name
  }
}

module "read_iam" {
  source = "../modules/read-iam"

  role_name           = "${local.name_prefix}-read-role"
  sightings_table_arn = module.sightings_table.table_arn
}

module "static_site" {
  source = "../modules/static-site"

  bucket_name       = "${local.name_prefix}-site-${random_id.site_bucket_suffix.hex}"
  distribution_name = "${local.name_prefix}-site"
}

module "read_api" {
  source = "../modules/http-api"

  api_name                 = "${local.name_prefix}-read-api"
  lambda_function_arn      = module.read_lambda.function_arn
  lambda_function_name     = module.read_lambda.function_name
  allowed_origins          = [module.static_site.site_url]
  sightings_throttle_rate  = var.sightings_throttle_rate
  sightings_throttle_burst = var.sightings_throttle_burst
  health_throttle_rate     = var.health_throttle_rate
  health_throttle_burst    = var.health_throttle_burst
}

resource "aws_s3_object" "site_asset" {
  for_each = local.site_asset_files

  bucket        = module.static_site.bucket_name
  key           = each.value
  source        = "${local.site_directory}/${each.value}"
  etag          = filemd5("${local.site_directory}/${each.value}")
  cache_control = "public, max-age=300"
  content_type = lookup(
    local.site_content_types,
    element(reverse(split(".", each.value)), 0),
    "application/octet-stream",
  )
}

resource "aws_s3_object" "site_config" {
  bucket        = module.static_site.bucket_name
  key           = "config.js"
  content       = templatefile("${local.site_directory}/config.js.tftpl", { api_endpoint = module.read_api.endpoint })
  etag          = md5(templatefile("${local.site_directory}/config.js.tftpl", { api_endpoint = module.read_api.endpoint }))
  cache_control = "public, max-age=300"
  content_type  = local.site_content_types.js
}

module "raw_object_processor" {
  source = "../modules/s3-lambda-notification"

  bucket_name          = module.raw_bucket.bucket_name
  bucket_arn           = module.raw_bucket.bucket_arn
  lambda_function_arn  = module.processor_lambda.function_arn
  lambda_function_name = module.processor_lambda.function_name
}

resource "aws_cloudwatch_log_group" "lambda" {
  # Create groups before their functions can be invoked and auto-create them.
  for_each = local.lambda_function_names

  name              = "/aws/lambda/${each.value}"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_metric_filter" "processor_completed" {
  name           = "${local.name_prefix}-processor-completed"
  log_group_name = aws_cloudwatch_log_group.lambda["processor"].name
  pattern        = "{ $.event = \"processing_completed\" }"

  metric_transformation {
    name      = "${local.name_prefix}-processor-completed"
    namespace = "BirdAlert/Operations"
    value     = "1"
  }
}

resource "aws_sns_topic" "operational_alarms" {
  name = "${local.name_prefix}-operational-alarms"
}

resource "aws_sns_topic_subscription" "alarm_email" {
  count = var.alarm_email == null ? 0 : 1

  topic_arn = aws_sns_topic.operational_alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = {
    poller    = module.poller_lambda.function_name
    processor = module.processor_lambda.function_name
  }

  alarm_name          = "${local.name_prefix}-${each.key}-errors"
  alarm_description   = "BirdAlert ${each.key} Lambda has failed."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 900
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.operational_alarms.arn]

  dimensions = {
    FunctionName = each.value
  }
}

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  for_each = {
    poller    = module.poller_dlq.queue_arn
    processor = module.processor_dlq.queue_arn
  }

  alarm_name          = "${local.name_prefix}-${each.key}-dlq-messages"
  alarm_description   = "BirdAlert ${each.key} DLQ contains failed events."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.operational_alarms.arn]

  dimensions = {
    QueueName = each.key == "poller" ? "${local.name_prefix}-poller-dlq" : "${local.name_prefix}-processor-dlq"
  }
}

resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name          = "${local.name_prefix}-api-5xx"
  alarm_description   = "BirdAlert API has sustained server errors."
  namespace           = "AWS/ApiGateway"
  metric_name         = "5xx"
  statistic           = "Sum"
  period              = 900
  evaluation_periods  = 1
  threshold           = 3
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.operational_alarms.arn]

  dimensions = {
    ApiId = module.read_api.api_id
    Stage = "$default"
  }
}

resource "aws_cloudwatch_metric_alarm" "processor_stale" {
  alarm_name          = "${local.name_prefix}-processor-stale"
  alarm_description   = "BirdAlert has not completed raw-object processing for 45 minutes."
  namespace           = "BirdAlert/Operations"
  metric_name         = "${local.name_prefix}-processor-completed"
  statistic           = "Sum"
  period              = 900
  evaluation_periods  = 3
  datapoints_to_alarm = 3
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.operational_alarms.arn]
}
