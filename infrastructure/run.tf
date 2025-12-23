module "cloud_run" {
  source = "./modules/gcp/docker_based_cloud_run"

  project_id                     = local.project_id
  region                         = var.region
  environment                    = var.environment
  system                         = var.system
  image_name                     = "podcast-automator"
  docker_context_path            = "${path.module}/.."
  docker_build_command           = "make -C app docker-build"
  docker_build_result_image_name = "podcast-automator:latest"
  service_account_email          = local.default_compute_service_account

  timeout_seconds    = var.function_timeout_seconds
  memory             = var.function_available_memory_gib
  max_instance_count = var.function_max_instance_count

  environment_variables = {
    INPUT_BUCKET              = google_storage_bucket.input.name
    DISCORD_WEBHOOK_INFO_URL  = data.google_secret_manager_secret_version.discord_webhook_info.secret_data
    DISCORD_WEBHOOK_ERROR_URL = data.google_secret_manager_secret_version.discord_webhook_error.secret_data
  }

  depends_on = [google_project_service.required]
}
