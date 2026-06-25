output "podcast_ui_service_account_email" {
  description = "Service account used by the podcast-ui server runtime."
  value       = google_service_account.podcast_ui.email
}

output "cloud_sql_instance_connection_name" {
  description = "Cloud SQL connection name used by Vercel and Cloud Run."
  value       = google_sql_database_instance.podcast.connection_name
}

output "cloud_sql_database_name" {
  description = "Application database name."
  value       = google_sql_database.podcast.name
}

output "cloud_sql_database_user" {
  description = "Application database user."
  value       = google_sql_user.podcast.name
}

output "cloud_sql_database_password_secret_name" {
  description = "Secret Manager secret containing the application database password."
  value       = google_secret_manager_secret.database_password.secret_id
}
