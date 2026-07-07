# creates IAM role and policies required by poller lambda function
module "poller_iam" {
  source    = "../modules/iam"
  role_name = "${local.name_prefix}-poller-role"
}
