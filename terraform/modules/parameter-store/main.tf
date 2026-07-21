resource "aws_ssm_parameter" "this" {
  name  = var.parameter_name
  type  = "SecureString"
  value = var.parameter_value
}
