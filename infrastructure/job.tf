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
    GCS_BUCKET = google_storage_bucket.input.name
    PROJECT_ID = var.project_id
    # TODO: remove DISCORD_WEBHOOK_INFO_URL; scheduled for deletion.
    DISCORD_WEBHOOK_INFO_URL = data.google_secret_manager_secret_version.discord_webhook_info.secret_data
    # TODO: remove DISCORD_WEBHOOK_ERROR_URL; scheduled for deletion.
    DISCORD_WEBHOOK_ERROR_URL         = data.google_secret_manager_secret_version.discord_webhook_error.secret_data
    DISCORD_WEBHOOK_INFO_SECRET_NAME  = var.discord_webhook_info_secret_name
    DISCORD_WEBHOOK_ERROR_SECRET_NAME = var.discord_webhook_error_secret_name
    R2_BUCKET                         = var.r2_bucket_name
    R2_KEY_PREFIX                     = var.r2_key_prefix
    R2_CUSTOM_DOMAIN                  = local.r2_custom_domain
    # TODO: remove CLOUDFLARE_ACCOUNT_ID; scheduled for deletion.
    CLOUDFLARE_ACCOUNT_ID    = var.cloudflare_account_id
    CLOUDFLARE_ACCESS_KEY_ID = data.google_secret_manager_secret_version.cloudflare_access_key_id.secret_data
    # TODO: remove CLOUDFLARE_SECRET_ACCESS_KEY; scheduled for deletion.
    CLOUDFLARE_SECRET_ACCESS_KEY             = data.google_secret_manager_secret_version.cloudflare_secret_access_key.secret_data
    CLOUDFLARE_ACCESS_KEY_ID_SECRET_NAME     = var.cloudflare_access_key_id_secret_name
    CLOUDFLARE_SECRET_ACCESS_KEY_SECRET_NAME = var.cloudflare_secret_access_key_secret_name
  }

  depends_on = [google_project_service.required]
}
