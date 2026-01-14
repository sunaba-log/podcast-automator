output "job_name" {
  description = "Cloud Run job name"
  value       = google_cloud_run_v2_job.job.name
}
