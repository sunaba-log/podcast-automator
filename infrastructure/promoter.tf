# promoter-job: 毎時間 X へ自動投稿をチェックし、古いものを1件投稿する
#
# 設計方針:
# - app job と同一の Docker イメージを local.app_image_uri 経由で参照
#   (Dockerfile・Docker build の追加なし)
# - command フィールドで ENTRYPOINT を override し promoter_main モジュールを実行
# - Secret 値は Secret Manager から Cloud Run に安全に注入する (value_source.secret_key_ref を使用)
# - Cloud Scheduler から Job を起動

resource "google_cloud_run_v2_job" "promoter" {
  name                = "${var.system}-promoter-${var.environment}"
  location            = var.region
  deletion_protection = false

  template {
    template {
      service_account = local.default_compute_service_account
      timeout         = "300s"

      containers {
        # app job と同一イメージを参照
        image = local.app_image_uri

        # Docker ENTRYPOINT を override して promoter_main モジュールを実行
        command = ["python", "-m", "promoter_main"]

        resources {
          limits = {
            memory = "512Mi"
            cpu    = "1"
          }
        }

        # Project ID
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }

        # X API secrets from Secret Manager
        env {
          name = "X_API_KEY"
          value_source {
            secret_key_ref {
              secret  = var.x_api_key_secret_name
              version = "latest"
            }
          }
        }

        env {
          name = "X_API_SECRET"
          value_source {
            secret_key_ref {
              secret  = var.x_api_secret_secret_name
              version = "latest"
            }
          }
        }

        env {
          name = "X_ACCESS_TOKEN"
          value_source {
            secret_key_ref {
              secret  = var.x_access_token_secret_name
              version = "latest"
            }
          }
        }

        env {
          name = "X_ACCESS_TOKEN_SECRET"
          value_source {
            secret_key_ref {
              secret  = var.x_access_token_secret_secret_name
              version = "latest"
            }
          }
        }
      }
    }
  }

  depends_on = [
    module.cloud_run_job,
    google_project_service.required,
  ]
}

# Cloud Scheduler: 毎時間
resource "google_cloud_scheduler_job" "promoter" {
  name             = "${var.system}-promoter-${var.environment}"
  description      = "Scheduled auto post to X (every hour)"
  schedule         = var.promoter_scheduler_cron
  time_zone        = "Asia/Tokyo"
  attempt_deadline = "320s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.promoter.name}:run"

    oauth_token {
      service_account_email = local.default_compute_service_account
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [
    google_cloud_run_v2_job.promoter,
    google_project_service.required,
    google_service_account_iam_member.cloud_scheduler_sa_token_creator,
  ]
}
