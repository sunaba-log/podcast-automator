resource "google_storage_bucket_iam_member" "function_input_access" {
  bucket = google_storage_bucket.input.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${local.default_compute_service_account}"
}

resource "google_project_iam_member" "function_logging" {
  project = local.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${local.default_compute_service_account}"
}

resource "google_project_iam_member" "function_vertex_ai" {
  project = local.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${local.default_compute_service_account}"
}

resource "google_project_iam_member" "eventarc_receiver" {
  project = local.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${local.default_compute_service_account}"
}

resource "google_project_iam_member" "eventarc_pubsub" {
  project = local.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${local.default_compute_service_account}"
}

resource "google_cloud_run_service_iam_member" "eventarc_invoke" {
  location = var.region
  service  = google_cloudfunctions2_function.processor.service_config[0].service
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.default_compute_service_account}"
}
