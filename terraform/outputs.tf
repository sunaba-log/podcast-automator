output "input_bucket_name" {
  value       = module.storage.input_bucket_name
  description = "GCS Input bucket name"
}

output "output_bucket_name" {
  value       = module.storage.output_bucket_name
  description = "GCS Output bucket name"
}

output "service_account_email" {
  value       = module.compute.service_account_email
  description = "Service Account email for Cloud Run Jobs"
}

output "cloud_run_job_name" {
  value       = module.compute.job_name
  description = "Cloud Run Job name"
}

output "cloud_run_job_location" {
  value       = var.region
  description = "Cloud Run Job location"
}

output "eventarc_trigger_name" {
  value       = module.trigger.eventarc_trigger_name
  description = "Eventarc trigger name"
}

output "secret_manager_secrets" {
  value = {
    r2_keys           = module.secrets.r2_keys_secret_id
    discord_webhook   = module.secrets.discord_webhook_secret_id
  }
  description = "Secret Manager secret IDs"
}
