# Mocked providers only: these checks do not contact AWS or change deployed state.
mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}"
    }
  }

  mock_resource "aws_iam_role" {
    defaults = {
      arn = "arn:aws:iam::123456789012:role/test-role"
    }
  }

  mock_resource "aws_s3_bucket" {
    defaults = {
      arn = "arn:aws:s3:::birdalert-test-bucket"
    }
  }

  mock_resource "aws_iam_policy" {
    defaults = {
      arn = "arn:aws:iam::123456789012:policy/test-policy"
    }
  }

  mock_resource "aws_sns_topic" {
    defaults = {
      arn = "arn:aws:sns:eu-west-1:123456789012:test-alarms"
    }
  }

  mock_resource "aws_lambda_function" {
    defaults = {
      arn = "arn:aws:lambda:eu-west-1:123456789012:function:test-function"
    }
  }

  mock_resource "aws_cloudwatch_event_rule" {
    defaults = {
      arn = "arn:aws:events:eu-west-1:123456789012:rule/test-schedule"
    }
  }

  mock_resource "aws_apigatewayv2_api" {
    defaults = {
      execution_arn = "arn:aws:execute-api:eu-west-1:123456789012:test-api"
    }
  }
}

mock_provider "random" {}

override_resource {
  target = module.poller_dlq.aws_sqs_queue.dlq
  values = {
    arn = "arn:aws:sqs:eu-west-1:123456789012:poller-dlq"
  }
}

override_resource {
  target = module.processor_dlq.aws_sqs_queue.dlq
  values = {
    arn = "arn:aws:sqs:eu-west-1:123456789012:processor-dlq"
  }
}

variables {
  aws_region         = "eu-west-1"
  environment        = "test"
  project_name       = "birdalert"
  ebird_regions      = ["GB-ENG"]
  raw_retention_days = 1
  ebird_api_key      = "test-placeholder"
}

run "poller_execution_failures_use_poller_queue" {
  command = apply

  assert {
    condition = (
      aws_lambda_function_event_invoke_config.poller.function_name == module.poller_lambda.function_name &&
      one(one(aws_lambda_function_event_invoke_config.poller.destination_config).on_failure).destination == module.poller_dlq.queue_arn
    )
    error_message = "Exhausted poller executions must go to the existing poller DLQ."
  }

  assert {
    condition = (
      aws_lambda_function_event_invoke_config.poller.maximum_retry_attempts == 2 &&
      aws_lambda_function_event_invoke_config.poller.maximum_event_age_in_seconds == 3600
    )
    error_message = "Lambda execution retries must remain bounded separately from eBird request retries."
  }

  assert {
    # Each of four requests can consume separate connect/read timeouts, plus backoff.
    condition     = local.poller_timeout_seconds >= 4 * (30 + 30) + 1 + 2 + 4 + 30
    error_message = "The poller must have time for four network attempts, backoff, and AWS-call overhead."
  }
}

run "sequential_regions_have_additional_retry_budget" {
  command = plan

  variables {
    ebird_regions = ["GB-ENG", "GB-SCT"]
  }

  assert {
    condition     = local.poller_timeout_seconds >= 2 * (4 * (30 + 30) + 1 + 2 + 4) + 30
    error_message = "The Lambda retry budget must account for regions being polled sequentially."
  }
}

run "timeout_stays_within_lambda_limit" {
  command = plan

  variables {
    ebird_regions = ["GB-ENG", "GB-SCT", "GB-WLS", "GB-NIR"]
  }

  assert {
    condition     = local.poller_timeout_seconds <= 900
    error_message = "The poller timeout must not exceed Lambda's 900-second limit."
  }
}
