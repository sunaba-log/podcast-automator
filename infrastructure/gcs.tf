resource "google_storage_bucket" "input" {
  name     = lower("${var.system}-audio-input-${var.environment}")
  location = var.region

  uniform_bucket_level_access = true
}
