data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type = "Service"

      identifiers = [
        "lambda.amazonaws.com"
      ]
    }

    actions = [
      "sts:AssumeRole"
    ]
  }
}

data "aws_iam_policy_document" "lambda_logging" {
  statement {
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${trimsuffix(var.log_group_arn, ":*")}:log-stream:*"
    ]
  }
}

data "aws_iam_policy_document" "parameter_store" {
  statement {
    effect = "Allow"

    actions = [
      "ssm:GetParameter"
    ]

    resources = [
      var.parameter_arn
    ]
  }
}

data "aws_iam_policy_document" "raw_bucket" {
  statement {
    effect = "Allow"

    actions = [
      "s3:PutObject"
    ]

    resources = [
      "${var.bucket_arn}/*"
    ]
  }
}

data "aws_iam_policy_document" "poller_dlq" {
  statement {
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [var.poller_dlq_arn]
  }
}
