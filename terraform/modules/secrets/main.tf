# Secret: Cloudflare R2 認証情報
resource "google_secret_manager_secret" "r2_keys" {
  secret_id = "cloudflare-r2-keys"
  replication {
    automatic = true
  }
}

# Secret: Discord Webhook URL
resource "google_secret_manager_secret" "discord_webhook" {
  secret_id = "discord-webhook-url"
  replication {
    automatic = true
  }
}

# Secret: Vertex AI API キー（オプション）
resource "google_secret_manager_secret" "vertex_ai_key" {
  secret_id = "vertex-ai-api-key"
  replication {
    automatic = true
  }
}

# NOTE: シークレット値は手動で設定してください（Terraform外で管理推奨）
# gcloud secret versions add cloudflare-r2-keys --data-file=- <<< '{"access_key_id":"xxx","secret_access_key":"yyy"}'

output "r2_keys_secret_id" {
  value = google_secret_manager_secret.r2_keys.id
}

output "discord_webhook_secret_id" {
  value = google_secret_manager_secret.discord_webhook.id
}
