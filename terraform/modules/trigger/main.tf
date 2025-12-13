# Pub/Sub Topic for orchestration (optional)
resource "google_pubsub_topic" "processor_jobs" {
  name = "podcast-processor-jobs"
}

# Eventarc Trigger: GCS -> Cloud Run Job
resource "google_eventarc_trigger" "gcs_processor" {
  name     = "gcs-to-processor-job"
  location = var.region
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = var.input_bucket
  }

  destination {
    cloud_run_job {
      job = var.cloud_run_job_name
    }
  }

  service_account = google_service_account.eventarc_sa.email
}

# Service Account for Eventarc
resource "google_service_account" "eventarc_sa" {
  account_id   = "eventarc-processor-sa"
  display_name = "Service Account for Eventarc trigger"
}

# IAM: Eventarc が Cloud Run Job を実行する権限
resource "google_project_iam_member" "eventarc_run_jobs" {
  project = var.project_id
  role    = "roles/run.jobs.editor"
  member  = "serviceAccount:${google_service_account.eventarc_sa.email}"
}

# IAM: Eventarc が イベントを受け取る権限
resource "google_project_iam_member" "eventarc_events_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc_sa.email}"
}

output "eventarc_trigger_name" {
  value = google_eventarc_trigger.gcs_processor.name
}
