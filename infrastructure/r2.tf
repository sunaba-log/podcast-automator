resource "cloudflare_r2_bucket" "podcast_assets" {
  account_id = var.cloudflare_account_id
  name       = var.r2_bucket_name
}
