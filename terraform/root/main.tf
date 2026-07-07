module "poller_iam" {
  source    = "../modules/iam"
  role_name = "${local.name_prefix}-poller_role"
}
