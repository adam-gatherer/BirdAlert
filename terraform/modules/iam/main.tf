resource "aws_iam_role" "lambda" {
  name = var.role_name

  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_policy" "lambda_logging" {
  name   = "${var.role_name}-logging"
  policy = data.aws_iam_policy_document.lambda_logging.json
}

resource "aws_iam_role_policy_attachment" "lambda_logging" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_policy" "parameter_store" {
  name   = "${var.role_name}-parameter-store"
  policy = data.aws_iam_policy_document.parameter_store.json
}

resource "aws_iam_role_policy_attachment" "parameter_store" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.parameter_store.arn
}

resource "aws_iam_policy" "raw_bucket" {
  name   = "${var.role_name}-raw-bucket"
  policy = data.aws_iam_policy_document.raw_bucket.json
}

resource "aws_iam_role_policy_attachment" "raw_bucket" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.raw_bucket.arn
}

resource "aws_iam_policy" "poller_dlq" {
  name   = "${var.role_name}-poller-dlq"
  policy = data.aws_iam_policy_document.poller_dlq.json
}

resource "aws_iam_role_policy_attachment" "poller_dlq" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.poller_dlq.arn
}
