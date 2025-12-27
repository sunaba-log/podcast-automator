resource "google_eventarc_trigger" "gcs_finalize" {
  name            = lower("${var.system}-gcs-finalize-${var.environment}")
  location        = var.region
  service_account = local.default_compute_service_account

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }

  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.input.name
  }

  destination {
    workflow = google_workflows_workflow.main.id
  }

  depends_on = [
    google_project_service.required,
    module.cloud_run_job,
    google_workflows_workflow.main,
    google_project_iam_member.eventarc_service_agent,
  ]
}
