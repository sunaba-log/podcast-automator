# 必要なAPIを有効化
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "containerregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
    "eventarc.googleapis.com",
    "pubsub.googleapis.com",
    "logging.googleapis.com"
  ])

  service            = each.value
  disable_on_destroy = false
}

# Artifact Registry Repository
resource "google_artifact_registry_repository" "podcast_repo" {
  location      = var.region
  repository_id = "podcast-processor"
  description   = "Container images for podcast processor"
  format        = "DOCKER"

  depends_on = [google_project_service.required_apis["artifactregistry.googleapis.com"]]
}

output "artifact_registry_repository" {
  value = google_artifact_registry_repository.podcast_repo.repository_url
}
