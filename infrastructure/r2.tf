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

resource "aws_s3_bucket_lifecycle_configuration" "r2_dev_expire" {
  provider = aws.r2
  count    = var.environment == "dev" ? 1 : 0
  bucket   = var.r2_bucket_name

  rule {
    id     = "expire-objects-3d"
    status = "Enabled"

    expiration {
      days = 3
    }
  }
}
