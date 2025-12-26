data "google_project" "project" {
  project_id = var.project_id
}

data "google_secret_manager_secret_version" "discord_webhook_info" {
  secret = var.discord_webhook_info_secret_name
}

data "google_secret_manager_secret_version" "discord_webhook_error" {
  secret = var.discord_webhook_error_secret_name
}
