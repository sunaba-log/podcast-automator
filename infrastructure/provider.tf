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

provider "cloudflare" {}
