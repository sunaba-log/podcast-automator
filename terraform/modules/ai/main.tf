# IAM: ジョブが Vertex AI モデル（Gemini 1.5 Pro など）を使用する権限
resource "google_project_iam_member" "job_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${var.service_account_email}"
}

# IAM: ジョブが Vertex AI API を呼び出す権限
resource "google_project_iam_member" "job_aiplatform_service_agent" {
  project = var.project_id
  role    = "roles/aiplatform.serviceAgent"
  member  = "serviceAccount:${var.service_account_email}"
}
