resource "google_service_account" "podcast_ui" {
  account_id   = "podcast-ui-${var.environment}"
  display_name = "Podcast UI ${var.environment}"
  project      = var.project_id
}

resource "google_storage_bucket_iam_member" "podcast_ui_upload" {
  bucket = google_storage_bucket.input.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.podcast_ui.email}"
}

resource "google_project_iam_member" "podcast_ui_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.podcast_ui.email}"
}

resource "google_project_iam_member" "podcast_ui_firebase_auth" {
  project = var.project_id
  role    = "roles/firebaseauth.admin"
  member  = "serviceAccount:${google_service_account.podcast_ui.email}"
}

resource "google_project_iam_member" "podcast_ui_cloud_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.podcast_ui.email}"
}
