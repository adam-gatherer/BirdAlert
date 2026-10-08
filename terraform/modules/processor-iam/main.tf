resource "aws_iam_role" "processor" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_policy" "lambda_logging" {
  name   = "${var.role_name}-logging"
  policy = data.aws_iam_policy_document.lambda_logging.json
}

resource "aws_iam_role_policy_attachment" "lambda_logging" {
  role       = aws_iam_role.processor.name
  policy_arn = aws_iam_policy.lambda_logging.arn
}

resource "aws_iam_policy" "raw_bucket_read" {
  name   = "${var.role_name}-raw-bucket-read"
  policy = data.aws_iam_policy_document.raw_bucket_read.json
}

resource "aws_iam_role_policy_attachment" "raw_bucket_read" {
  role       = aws_iam_role.processor.name
  policy_arn = aws_iam_policy.raw_bucket_read.arn
}
