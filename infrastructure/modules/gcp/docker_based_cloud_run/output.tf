output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.service.name
}
