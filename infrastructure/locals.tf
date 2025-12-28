locals {
  required_services = [
    "artifactregistry.googleapis.com",
    "compute.googleapis.com",
    "eventarc.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",
    "workflows.googleapis.com",
  ]

  default_compute_service_account = "${data.google_project.project.number}-compute@developer.gserviceaccount.com"

  r2_custom_domain = "${var.r2_subdomain}.${var.cloudflare_zone_name}"
}
