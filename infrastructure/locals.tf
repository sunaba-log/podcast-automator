locals {
  project_id = lower("${var.system}-${var.environment}")

  required_services = [
    "artifactregistry.googleapis.com",
    "eventarc.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
  ]

  default_compute_service_account = "${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}
