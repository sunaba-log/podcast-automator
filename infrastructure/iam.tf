resource "google_storage_bucket_iam_member" "cloud_run_input_access" {
  bucket = google_storage_bucket.input.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "cloud_run_logging" {
  project = local.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "cloud_run_vertex_ai" {
  project = local.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "eventarc_receiver" {
  project = local.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "eventarc_pubsub" {
  project = local.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service_iam_member" "eventarc_invoke" {
  location = var.region
  name     = module.cloud_run.service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}
