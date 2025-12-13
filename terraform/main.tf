terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# ================================
# Module: Core (API有効化等)
# ================================
module "core" {
  source = "./modules/core"

  project_id = var.project_id
  region     = var.region
}

# ================================
# Module: Storage (GCS バケット)
# ================================
module "storage" {
  source = "./modules/storage"

  project_id      = var.project_id
  region          = var.region
  environment     = var.environment
  input_bucket    = var.input_bucket_name
  output_bucket   = var.output_bucket_name
}

# ================================
# Module: Secrets (Secret Manager)
# ================================
module "secrets" {
  source = "./modules/secrets"

  project_id = var.project_id
}

# ================================
# Module: Compute (Cloud Run Jobs & SA)
# ================================
module "compute" {
  source = "./modules/compute"

  project_id      = var.project_id
  region          = var.region
  environment     = var.environment
  service_name    = var.service_name
  container_image = var.container_image

  depends_on = [module.core, module.secrets]
}

# ================================
# Module: Trigger (Eventarc & Pub/Sub)
# ================================
module "trigger" {
  source = "./modules/trigger"

  project_id              = var.project_id
  region                  = var.region
  input_bucket            = module.storage.input_bucket_name
  cloud_run_job_name      = module.compute.job_name
  cloud_run_job_location  = var.region

  depends_on = [module.storage, module.compute]
}

# ================================
# Module: AI (Vertex AI IAM)
# ================================
module "ai" {
  source = "./modules/ai"

  project_id         = var.project_id
  service_account_email = module.compute.service_account_email
}
