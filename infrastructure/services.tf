resource "google_project_service" "required" {
  for_each = toset(local.required_services)

  service            = each.value
  disable_on_destroy = false
}

resource "google_project_service_identity" "eventarc" {
  provider   = google-beta
  service    = "eventarc.googleapis.com"
  depends_on = [google_project_service.required]
}

resource "google_project_service_identity" "aiplatform" {
  provider   = google-beta
  service    = "aiplatform.googleapis.com"
  depends_on = [google_project_service.required]
}
