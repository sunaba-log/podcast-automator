resource "google_eventarc_trigger" "gcs_finalize" {
  name     = lower("${var.system}-gcs-finalize-${var.environment}")
  location = var.region

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }

  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.input.name
  }

  destination {
    cloud_run_service {
      service = module.cloud_run.service_name
      region  = var.region
    }
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_service.processor,
  ]
}
