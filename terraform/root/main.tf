# creates the raw bucket for dumping API data
module "raw_bucket" {
  source = "../modules/s3"

  bucket_name    = "${local.name_prefix}-raw"
  retention_days = var.raw_retention_days
}

# creates the poller lambda function using the zipped app.py in /build
module "poller_lambda" {
  source = "../modules/lambda"

  function_name = "${local.name_prefix}-poller"

  role_arn = module.poller_iam.role_arn

  filename = "../../build/poller.zip"

  handler = "app.lambda_handler"

  runtime = "python3.13"

  bucket_name    = module.raw_bucket.bucket_name
  parameter_name = module.ebird_api_key.parameter_name
  ebird_regions  = var.ebird_regions
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

  rule_name            = "${local.name_prefix}-poller-schedule"
  schedule_expression  = "rate(15 minutes)"
  lambda_function_arn  = module.poller_lambda.function_arn
  lambda_function_name = module.poller_lambda.function_name
}
