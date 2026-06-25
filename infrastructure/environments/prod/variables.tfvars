environment        = "prod"
system             = "podcast-automator"
project_id         = "sunabalog-prod"
gcs_force_destroy  = false
gcs_retention_days = 30
gcs_cors_origins = [
  "https://podcast-ui-kentakashimas-projects.vercel.app",
  "https://podcast-ui-red.vercel.app",
  "https://podcast-ui-git-main-kentakashimas-projects.vercel.app",
]
discord_webhook_info_secret_name   = "discord-webhook-url-prod-info"
discord_webhook_error_secret_name  = "discord-webhook-url-prod-error"
discord_webhook_agenda_secret_name = "discord-webhook-url-prod-agenda"
cloudflare_account_id              = "8ed20f6872cea7c9219d68bfcf5f98ae"
cloudflare_zone_name               = "sunabalog.com"
r2_bucket_name                     = "podcast"
r2_subdomain                       = "podcast"
podcast_id                         = "1"
database_url_secret_name           = "podcast-database-url-prod"
cloud_sql_tier                     = "db-custom-1-3840"
