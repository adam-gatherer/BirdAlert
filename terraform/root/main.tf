# Stable eight-character suffix prevents global S3 naming collisions.
resource "random_id" "raw_bucket_suffix" {
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

  function_name = "${local.name_prefix}-poller"

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

# processes each raw response after it lands in S3
module "processor_lambda" {
  source = "../modules/lambda"

  function_name = "${local.name_prefix}-processor"
  role_arn      = module.processor_iam.role_arn
  filename      = "../../build/processor.zip"
  handler       = "app.lambda_handler"
  runtime       = "python3.13"

  environment_variables = {
    SIGHTINGS_TABLE = module.sightings_table.table_name
  }
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
}

# Serves bounded public read requests from DynamoDB; it never reads raw S3 data.
module "read_lambda" {
  source = "../modules/lambda"

  function_name = "${local.name_prefix}-read"
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

module "read_api" {
  source = "../modules/http-api"

  api_name                 = "${local.name_prefix}-read-api"
  lambda_function_arn      = module.read_lambda.function_arn
  lambda_function_name     = module.read_lambda.function_name
  allowed_origins          = var.api_allowed_origins
  sightings_throttle_rate  = var.sightings_throttle_rate
  sightings_throttle_burst = var.sightings_throttle_burst
  health_throttle_rate     = var.health_throttle_rate
  health_throttle_burst    = var.health_throttle_burst
}

module "raw_object_processor" {
  source = "../modules/s3-lambda-notification"

  bucket_name          = module.raw_bucket.bucket_name
  bucket_arn           = module.raw_bucket.bucket_arn
  lambda_function_arn  = module.processor_lambda.function_arn
  lambda_function_name = module.processor_lambda.function_name
}
