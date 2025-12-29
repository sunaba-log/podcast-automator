resource "google_artifact_registry_repository_iam_member" "reader" {
  location   = var.region
  repository = module.docker_image.repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${var.service_account_email}"
}
