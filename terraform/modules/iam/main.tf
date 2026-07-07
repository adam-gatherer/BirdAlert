resource "aws_iam_role" "lambda" {
  name = var.role_name

  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}
