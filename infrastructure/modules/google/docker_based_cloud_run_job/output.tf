output "job_name" {
  description = "Cloud Run job name"
  value       = google_cloud_run_v2_job.job.name
}

output "docker_image_name" {
  description = "Full name (with digest tag) of the built and pushed Docker image"
  value       = module.docker_image.docker_image_name
}
