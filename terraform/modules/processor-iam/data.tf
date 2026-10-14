data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "lambda_logging" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "raw_bucket_read" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${var.bucket_arn}/*"]
  }
}

data "aws_iam_policy_document" "sightings_write" {
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [var.sightings_table_arn]
  }
}
