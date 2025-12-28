terraform {
  required_version = ">= 1.14.3"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.14"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 7.14"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.25"
    }
  }

  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region

  default_labels = {
    org         = var.org
    environment = var.environment
    system      = var.system
  }
}

provider "google-beta" {
  project = var.project_id
  region  = var.region

  default_labels = {
    org         = var.org
    environment = var.environment
    system      = var.system
  }
}

provider "aws" {
  alias      = "r2"
  region     = var.region
  access_key = var.cloudflare_access_key_id
  secret_key = var.cloudflare_secret_access_key

  skip_credentials_validation = true
  skip_region_validation      = true
  skip_requesting_account_id  = true

  endpoints {
    s3 = "https://${var.cloudflare_account_id}.r2.cloudflarestorage.com"
  }
}

provider "cloudflare" {}
