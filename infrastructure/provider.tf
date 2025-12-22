terraform {
  required_version = ">= 1.14.2"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {}
}

provider "google" {
  project = local.project_id
  region  = var.region

  default_labels = {
    org         = "sunaba-log"
    environment = var.environment
    system      = var.system
  }
}
