# creates IAM role and policies required by poller lambda function
module "poller_iam" {
  source    = "../modules/iam"
  role_name = "${local.name_prefix}-poller-role"
}

# creates the raw bucket for dumping API data
module "raw_bucket" {
  source = "../modules/s3"

  bucket_name = "${local.name_prefix}-raw"
}

# creates the poller lambda function using the zipped app.py in /build
module "poller_lambda" {
  source = "../modules/lambda"

  function_name = "${local.name_prefix}-poller"

  role_arn = module.poller_iam.role_arn

  filename = "../../build/poller.zip"

  handler = "app.lambda_handler"

  runtime = "python3.13"
}
