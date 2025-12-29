module "cloud_run_job" {
  source = "./modules/google/docker_based_cloud_run_job"

  project_id                     = var.project_id
  region                         = var.region
  environment                    = var.environment
  system                         = var.system
  image_name                     = "app"
  docker_context_path            = "${path.module}/../app"
  docker_build_command           = "make docker-build"
  docker_build_result_image_name = "podcast-automator-app:latest"
  job_name                       = "${var.system}-app-${var.environment}"
  service_account_email          = local.default_compute_service_account

  timeout            = "3600s"
  memory             = "8Gi"
  cpu                = "2"
  max_instance_count = 1

  environment_variables = {
    GCS_BUCKET                   = google_storage_bucket.input.name
    DISCORD_WEBHOOK_INFO_URL     = data.google_secret_manager_secret_version.discord_webhook_info.secret_data
    DISCORD_WEBHOOK_ERROR_URL    = data.google_secret_manager_secret_version.discord_webhook_error.secret_data
    R2_BUCKET                    = var.r2_bucket_name
    CLOUDFLARE_ACCOUNT_ID        = var.cloudflare_account_id
    CLOUDFLARE_ACCESS_KEY_ID     = data.google_secret_manager_secret_version.cloudflare_access_key_id.secret_data
    CLOUDFLARE_SECRET_ACCESS_KEY = data.google_secret_manager_secret_version.cloudflare_secret_access_key.secret_data
  }

  depends_on = [google_project_service.required]
}
