resource "google_storage_bucket" "input" {
  name     = lower("${var.system}-audio-input-${var.environment}")
  location = var.region

  uniform_bucket_level_access = true

  force_destroy = var.input_bucket_force_destroy

  dynamic "lifecycle_rule" {
    for_each = var.input_retention_days != null ? [1] : []
    content {
      condition {
        age = var.input_retention_days
      }
      action {
        type = "Delete"
      }
    }
  }
}
