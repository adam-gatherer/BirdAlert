# Inspect configured statements with mocked AWS data; never contact AWS.
mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }
}

variables {
  role_name           = "birdalert-test-role"
  log_group_arn       = "arn:aws:logs:eu-west-1:123456789012:log-group:/aws/lambda/birdalert-test-function"
  parameter_arn       = "arn:aws:ssm:eu-west-1:123456789012:parameter/birdalert/test/ebird/api-key"
  bucket_arn          = "arn:aws:s3:::birdalert-test-raw"
  poller_dlq_arn      = "arn:aws:sqs:eu-west-1:123456789012:poller-dlq"
  processor_dlq_arn   = "arn:aws:sqs:eu-west-1:123456789012:processor-dlq"
  sightings_table_arn = "arn:aws:dynamodb:eu-west-1:123456789012:table/birdalert-test-sightings"
}

run "poller_can_write_only_its_own_streams" {
  command = plan

  module {
    source = "../modules/iam"
  }

  assert {
    condition = (
      one(data.aws_iam_policy_document.lambda_logging.statement).actions == toset(["logs:CreateLogStream", "logs:PutLogEvents"]) &&
      one(data.aws_iam_policy_document.lambda_logging.statement).resources == toset(["${var.log_group_arn}:log-stream:*"])
    )
    error_message = "Poller logging must exclude log-group creation and access to other groups."
  }
}

run "processor_can_write_only_its_own_streams" {
  command = plan

  module {
    source = "../modules/processor-iam"
  }

  assert {
    condition = (
      one(data.aws_iam_policy_document.lambda_logging.statement).actions == toset(["logs:CreateLogStream", "logs:PutLogEvents"]) &&
      one(data.aws_iam_policy_document.lambda_logging.statement).resources == toset(["${var.log_group_arn}:log-stream:*"])
    )
    error_message = "Processor logging must exclude log-group creation and access to other groups."
  }
}

run "read_role_normalises_the_log_group_arn_suffix" {
  command = plan

  module {
    source = "../modules/read-iam"
  }

  variables {
    log_group_arn = "arn:aws:logs:eu-west-1:123456789012:log-group:/aws/lambda/birdalert-test-read:*"
  }

  assert {
    condition = (
      one(data.aws_iam_policy_document.lambda_logging.statement).actions == toset(["logs:CreateLogStream", "logs:PutLogEvents"]) &&
      one(data.aws_iam_policy_document.lambda_logging.statement).resources == toset(["arn:aws:logs:eu-west-1:123456789012:log-group:/aws/lambda/birdalert-test-read:log-stream:*"])
    )
    error_message = "Read logging must be scoped to its own streams, including legacy ARN suffix handling."
  }
}
