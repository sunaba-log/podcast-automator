# Service Account for Cloud Run Jobs
resource "google_service_account" "job_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name}"
}

# Cloud Run Job (placeholder - Vertex AI & R2 処理実行)
resource "google_cloud_run_v2_job" "processor_job" {
  name     = var.service_name
  location = var.region

  template {
    template {
      service_account = google_service_account.job_sa.email

      containers {
        image = var.container_image

        # 環境変数設定例
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
      }

      timeout = "600s"
      max_retries = 2
    }

    task_count = 1
  }

  labels = {
    environment = var.environment
  }
}

# IAM: ジョブが GCS を読み書きするための権限
resource "google_project_iam_member" "job_gcs_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.job_sa.email}"
}

# IAM: ジョブが Secret Manager にアクセスする権限
resource "google_project_iam_member" "job_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.job_sa.email}"
}

# IAM: ジョブが Vertex AI にアクセスする権限
resource "google_project_iam_member" "job_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.job_sa.email}"
}

output "service_account_email" {
  value = google_service_account.job_sa.email
}

output "job_name" {
  value = google_cloud_run_v2_job.processor_job.name
}
