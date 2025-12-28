resource "cloudflare_r2_bucket" "main" {
  account_id = var.cloudflare_account_id
  name       = var.r2_bucket_name

  lifecycle {
    prevent_destroy = var.environment == "prod"
  }
}

resource "cloudflare_r2_custom_domain" "main" {
  account_id  = var.cloudflare_account_id
  bucket_name = cloudflare_r2_bucket.main.name
  domain      = local.r2_custom_domain
  enabled     = true
  zone_id     = data.cloudflare_zone.main.id
}
