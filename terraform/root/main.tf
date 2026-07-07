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
