locals {
  project_id = lower("${var.system}-${var.environment}")

  required_services = [
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "eventarc.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
  ]
}
