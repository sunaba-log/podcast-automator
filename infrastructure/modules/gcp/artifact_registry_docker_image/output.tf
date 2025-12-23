output "repository_id" {
  description = "artifact registry repository id"
  value       = google_artifact_registry_repository.main.repository_id
}

output "repository_name" {
  description = "artifact registry repository name"
  value       = local.repository_name
}

output "repository_url" {
  description = "artifact registry repository url"
  value       = local.repository_url
}

output "docker_image_latest" {
  description = "latest tag for the built docker image"
  value       = local.docker_image_latest
}

output "docker_image_name" {
  description = "full name of the built and pushed docker image"
  value       = local.docker_image
}

output "docker_image_digest" {
  description = "digest of the built docker image"
  value       = data.external.docker_image_digest.result.digest
}

output "repository_outputs" {
  description = "artifact registry repository resource"
  value       = google_artifact_registry_repository.main
  depends_on  = [null_resource.docker_push]
}
