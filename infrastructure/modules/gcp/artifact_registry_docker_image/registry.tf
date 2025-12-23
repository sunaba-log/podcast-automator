resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = local.repository_name
  format        = "DOCKER"

  cleanup_policies {
    id     = "delete-older-than-0s"
    action = "DELETE"
    condition {
      tag_state  = "ANY"
      older_than = "0s"
    }
  }

  cleanup_policies {
    id     = "keep-most-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = var.image_keep_count
    }
  }
}
