output "podcast_ui_service_account_email" {
  description = "Service account used by the podcast-ui server runtime."
  value       = google_service_account.podcast_ui.email
}
