resource "google_cloudfunctions2_function" "processor" {
  name     = lower("${var.system}-processor-${var.environment}")
  location = var.region

  build_config {
    runtime     = var.function_runtime
    entry_point = var.function_entry_point

    source {
      storage_source {
        bucket = var.function_source_bucket
        object = var.function_source_object
      }
    }
  }

  service_config {
    available_memory      = var.function_available_memory_gib
    timeout_seconds       = var.function_timeout_seconds
    max_instance_count    = var.function_max_instance_count

    environment_variables = {
      INPUT_BUCKET          = google_storage_bucket.input.name
      DISCORD_WEBHOOK_INFO_URL  = data.google_secret_manager_secret_version.discord_webhook_info.secret_data
      DISCORD_WEBHOOK_ERROR_URL = data.google_secret_manager_secret_version.discord_webhook_error.secret_data
    }
  }

  depends_on = [google_project_service.required]
}
