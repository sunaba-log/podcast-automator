# Input Bucket (音声ファイルのアップロード先)
resource "google_storage_bucket" "input" {
  name          = var.input_bucket
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 30
    }
  }

  labels = {
    environment = var.environment
    purpose     = "input"
  }
}

# Output Bucket (処理済み音声・RSS出力先)
resource "google_storage_bucket" "output" {
  name          = var.output_bucket
  location      = var.region
  force_destroy = var.environment != "prod"

  uniform_bucket_level_access = true

  labels = {
    environment = var.environment
    purpose     = "output"
  }
}

output "input_bucket_name" {
  value = google_storage_bucket.input.name
}

output "output_bucket_name" {
  value = google_storage_bucket.output.name
}
