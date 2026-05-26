# agenda-job: 毎週水曜 07:00 JST に Discord へアジェンダを投稿する
#
# 設計方針:
# - app job と同一の Docker イメージを local.app_image_uri 経由で参照
#   (Dockerfile・Docker build の追加なし)
# - command フィールドで ENTRYPOINT を override し agenda_main モジュールを実行
# - Secret 値は Terraform state に保持しない (value_source.secret_key_ref を使用)
# - Cloud Scheduler サービスエージェントへの IAM は iam.tf で管理

# Cloud Run Job: agenda
resource "google_cloud_run_v2_job" "agenda" {
  name                = "${var.system}-agenda-${var.environment}"
  location            = var.region
  deletion_protection = false

  template {
    template {
      service_account = local.default_compute_service_account
      timeout         = "300s"

      containers {
        # app job と同一イメージを参照 (locals.tf の app_image_uri 経由)
        image = local.app_image_uri

        # Docker ENTRYPOINT を override して agenda_main モジュールを実行
        command = ["python", "-m", "agenda_main"]

        resources {
          limits = {
            memory = "512Mi"
            cpu    = "1"
          }
        }

        # Secret 値を Terraform state に保存しない: Cloud Run が実行時に Secret Manager から取得
        env {
          name = "DISCORD_WEBHOOK_AGENDA_URL"
          value_source {
            secret_key_ref {
              secret  = var.discord_webhook_agenda_secret_name
              version = "latest"
            }
          }
        }

        # Discord Bot Token (read-only): transcript チャンネルからメッセージ取得に使用
        # 未設定 (空文字列) の場合は transcript 取得をスキップし固定文 fallback へ移行
        env {
          name = "DISCORD_BOT_TOKEN"
          value_source {
            secret_key_ref {
              secret  = var.discord_bot_token_secret_name
              version = "latest"
            }
          }
        }

        # Discord transcript チャンネル ID (plain env var)
        # 空文字列の場合は transcript 取得をスキップ (fallback path を維持)
        env {
          name  = "DISCORD_TRANSCRIPT_CHANNEL_ID"
          value = var.discord_transcript_channel_id
        }
      }
    }
  }

  depends_on = [
    module.cloud_run_job,
    google_project_service.required,
  ]
}

# Cloud Scheduler: 毎週水曜 07:00 JST
resource "google_cloud_scheduler_job" "agenda" {
  name             = "${var.system}-agenda-${var.environment}"
  description      = "Weekly agenda notification to Discord (every Wednesday 07:00 JST)"
  schedule         = "0 7 * * 3"
  time_zone        = "Asia/Tokyo"
  attempt_deadline = "320s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.agenda.name}:run"

    # run.googleapis.com は Google 管理 API のため oauth_token を使用
    # (oidc_token は Cloud Run service など自前エンドポイント向け)
    oauth_token {
      service_account_email = local.default_compute_service_account
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [
    google_cloud_run_v2_job.agenda,
    google_project_service.required,
    google_service_account_iam_member.cloud_scheduler_sa_token_creator,
  ]
}
