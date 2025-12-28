resource "cloudflare_r2_bucket" "main" {
  account_id = var.cloudflare_account_id
  name       = var.r2_bucket_name
}

resource "cloudflare_r2_custom_domain" "main" {
  account_id  = var.cloudflare_account_id
  bucket_name = cloudflare_r2_bucket.main.name
  domain      = local.r2_custom_domain
  enabled     = true
  zone_id     = data.cloudflare_zone.main.id
}

resource "cloudflare_r2_bucket_lifecycle" "r2_expire" {
  count      = var.environment == "dev" ? 1 : 0
  account_id = var.cloudflare_account_id
  bucket_name = var.r2_bucket_name

  rules = [{
    id        = "expire-objects-${var.r2_retention_days}d"
    enabled   = true
    conditions = {
      prefix = ""
    }
    delete_objects_transition = {
      condition = {
        max_age = var.r2_retention_days * 86400
        type    = "Age"
      }
    }
  }]
}
