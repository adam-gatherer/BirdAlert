terraform {
  required_version = "~> 1.14"

  backend "s3" {
    # Environment-specific settings are supplied with -backend-config.
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }
}
