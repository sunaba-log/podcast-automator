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
      DISCORD_WEBHOOK_SECRET = local.discord_webhook_secret_id
      R2_ACCESS_KEY_ID_SECRET = local.r2_access_key_id_secret_id
      R2_SECRET_ACCESS_KEY_SECRET = local.r2_secret_access_key_secret_id
      R2_ENDPOINT_SECRET    = local.r2_endpoint_secret_id
      R2_BUCKET_NAME_SECRET = local.r2_bucket_name_secret_id
    }
  }

  depends_on = [google_project_service.required]
}
