environment        = "dev"
system             = "podcast-automator"
project_id         = "sunabalog-dev"
gcs_force_destroy  = true
gcs_retention_days = 3
gcs_cors_origins = [
  "http://localhost:3000",
  "http://localhost:3002",
  "https://podcast-ui-kentakashimas-projects.vercel.app",
  "https://podcast-ui-red.vercel.app",
  "https://podcast-ui-git-main-kentakashimas-projects.vercel.app",
  "https://podcast-ui-git-feature-16-episode-6d23e0-kentakashimas-projects.vercel.app",
]
discord_webhook_info_secret_name   = "discord-webhook-url-dev-info"
discord_webhook_error_secret_name  = "discord-webhook-url-dev-error"
discord_webhook_agenda_secret_name = "discord-webhook-url-dev-agenda"
discord_bot_token_secret_name      = "discord-bot-token-dev"
discord_transcript_channel_id      = "1452839882320908359"
podcast_id                         = "1"
database_url_secret_name           = "podcast-database-url-dev"
cloudflare_account_id              = "8ed20f6872cea7c9219d68bfcf5f98ae"
cloudflare_zone_name               = "sunabalog.com"
r2_bucket_name                     = "podcast-dev"
r2_subdomain                       = "dev.podcast"
enable_promoter                    = true
manage_firestore_database          = false