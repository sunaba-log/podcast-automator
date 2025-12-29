resource "google_storage_bucket_iam_member" "job_input_access" {
  bucket = google_storage_bucket.input.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "job_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "job_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "eventarc_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "eventarc_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "gcs_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gs-project-accounts.iam.gserviceaccount.com"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "workflows_invoker" {
  project = var.project_id
  role    = "roles/workflows.invoker"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "job_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "job_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${local.default_compute_service_account}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "eventarc_service_agent" {
  project = var.project_id
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:${google_project_service_identity.eventarc.email}"

  depends_on = [
    google_project_service.required,
    google_project_service_identity.eventarc,
  ]
}
