terraform {
  required_version = "~> 1.14"

  backend "s3" {
    bucket       = "birdalert-terraform-state-3a602f"
    key          = "birdalert/dev/terraform.tfstate"
    region       = "eu-west-1"
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
