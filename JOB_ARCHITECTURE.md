# Cloud Run Jobs - モジュール設計・実装ガイド

このドキュメントでは、podcast-automator で使用する Cloud Run Jobs の構成、各ジョブの役割、実装パターンを説明します。

## ジョブ構成概要

```
┌─────────────────────────────────────────────────────────────────┐
│ Event: GCS Object Finalize                                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Controller (Cloud Run Service)                                   │
│ - Eventarc から HTTP POST を受け取る                            │
│ - fetch-job を起動                                              │
│ - 完了・エラーを監視                                             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ fetch-job (Cloud Run Job)                                        │
│ - GCS から mp3 をダウンロード                                   │
│ - メタデータと共に process-job を起動                           │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ process-job (Cloud Run Job)                                      │
│ - Vertex AI (Gemini 1.5 Pro) で音声分析                        │
│ - タイトル、概要、議事録を生成                                   │
│ - メタデータと共に upload-job を起動                            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ upload-job (Cloud Run Job)                                       │
│ - Cloudflare R2 に音声・メタデータをアップロード                │
│ - RSS フィードを生成・公開                                      │
│ - notify-job を起動 (成功)                                     │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ notify-job (Cloud Run Job)                                       │
│ - 処理結果を Discord に通知                                     │
│ - 成功 / 失敗状態を報告                                         │
└─────────────────────────────────────────────────────────────────┘
```

## 各ジョブの詳細

### 1. Controller (Cloud Run Service)

**役割**

- Eventarc から GCS Object Finalize イベントを HTTP POST で受け取る
- fetch-job を起動（Cloud Run Jobs API）

**入力**

- Eventarc イベント (JSON)
  ```json
  {
    "bucket": "podcast-input-dev",
    "name": "episode-001.mp3"
  }
  ```

**出力**

- 202 Accepted
- Job ID を返却

**実装**

- `app/controller/main.py` (Flask アプリケーション)
- デプロイ形式: Cloud Run Service (常時実行)

**ビルド・デプロイ**

```bash
cd app/controller
docker build -t gcr.io/<project>/controller:latest .
docker push gcr.io/<project>/controller:latest

gcloud run deploy controller \
  --image gcr.io/<project>/controller:latest \
  --region asia-northeast1 \
  --allow-unauthenticated
```

---

### 2. fetch-job (Cloud Run Job)

**役割**

- GCS Input バケットから mp3 ファイルをダウンロード
- ローカル一時ストレージ（または GCS）に保存
- ファイル情報を次のジョブに渡す

**入力**

- コマンドラインパラメタ
  ```bash
  --job-id <UUID>
  --bucket podcast-input-dev
  --object-name episode-001.mp3
  --output-path /tmp/audio.mp3
  ```

**出力**

- stdout (JSON)
  ```json
  {
    "status": "success",
    "job_id": "uuid",
    "local_file": "/tmp/audio.mp3",
    "file_size": 50000000,
    "source_bucket": "podcast-input-dev",
    "source_object": "episode-001.mp3"
  }
  ```

**実装**

- `app/fetch-job/main.py`
- 共有ライブラリ: `shared.storage.GCSClient`

**環境変数**

- `GCP_PROJECT_ID` - GCP プロジェクト ID
- `GCS_INPUT_BUCKET` - Input バケット名

---

### 3. process-job (Cloud Run Job)

**役割**

- Vertex AI (Gemini 1.5 Pro) で音声を分析
- メタデータ (タイトル、概要、議事録) を生成

**入力**

- コマンドラインパラメタ
  ```bash
  --job-id <UUID>
  --audio-file /tmp/audio.mp3
  --gcs-uri gs://podcast-input-dev/episode-001.mp3
  ```

**出力**

- stdout (JSON)
  ```json
  {
    "status": "success",
    "job_id": "uuid",
    "metadata": {
      "title": "Episode Title",
      "summary": "A brief summary...",
      "transcript": "Full transcript...",
      "duration_seconds": 1800,
      "keywords": ["keyword1", "keyword2"]
    }
  }
  ```

**実装**

- `app/process-job/main.py`
- 共有ライブラリ: `shared.ai.VertexAIClient`

**環境変数**

- `VERTEX_AI_MODEL` - モデル名 (デフォルト: gemini-1.5-pro)
- `VERTEX_AI_LOCATION` - リージョン (デフォルト: asia-northeast1)

**注**: Vertex AI API の実装は別途必要。以下はプレースホルダ実装。

---

### 4. upload-job (Cloud Run Job)

**役割**

- メタデータ + 音声を Cloudflare R2 にアップロード
- RSS フィードを生成・公開
- 公開 URL を生成

**入力**

- コマンドラインパラメタ
  ```bash
  --job-id <UUID>
  --audio-file /tmp/audio.mp3
  --metadata-json '{"title":"...","summary":"...",...}'
  ```

**出力**

- stdout (JSON)
  ```json
  {
    "status": "success",
    "job_id": "uuid",
    "audio_url": "https://media.example.com/podcasts/uuid/audio.mp3",
    "metadata_key": "podcasts/uuid/metadata.json",
    "rss_key": "podcasts/uuid/feed.rss"
  }
  ```

**実装**

- `app/upload-job/main.py`
- 共有ライブラリ: `shared.cdn.R2Client`

**環境変数**

- `R2_ENDPOINT_URL` - R2 エンドポイント
- `R2_BUCKET` - R2 バケット名
- `R2_CUSTOM_DOMAIN` - カスタムドメイン (オプション)
- `R2_KEYS_SECRET_NAME` - Secret Manager シークレット名

---

### 5. notify-job (Cloud Run Job)

**役割**

- 処理完了 / エラーを Discord に通知
- ステータス、エラーメッセージ、出力 URL を含む

**入力**

- コマンドラインパラメタ
  ```bash
  --job-id <UUID>
  --status completed|failed
  --message "Processing completed successfully"
  --output-url https://media.example.com/podcasts/uuid/audio.mp3
  --error null
  ```

**出力**

- stdout (JSON)
  ```json
  {
    "status": "success",
    "job_id": "uuid",
    "notification_sent": true
  }
  ```

**実装**

- `app/notify-job/main.py`
- 共有ライブラリ: `shared.notifier.DiscordNotifier`

**環境変数**

- `DISCORD_WEBHOOK_SECRET_NAME` - Secret Manager シークレット名

---

## 共有ライブラリ (app/shared/)

各ジョブが共通で使用するライブラリ・ユーティリティ：

### config.py

環境変数管理。GCP、R2、Vertex AI、ロギングの設定。

### models.py

データクラス定義:

- `PodcastProcessingJob`: ジョブ全体の状態
- `ProcessingMetadata`: Vertex AI からのメタデータ

### storage.py

`GCSClient`: GCS ファイルの読み書き

### ai.py

`VertexAIClient`: Vertex AI API への送信

### cdn.py

`R2Client`: Cloudflare R2 (S3 互換) へのアップロード

### notifier.py

`DiscordNotifier`: Discord Webhook 通知

### logger.py

ロギング設定

---

## ジョブ間のデータフロー

### パターン 1: 逐次実行（推奨）

各ジョブが完了してから次のジョブを起動（Controller が管理）。

```
Controller → fetch-job → process-job → upload-job → notify-job
            (poll/wait)
```

**メリット**

- 失敗時の処理がシンプル
- リソース効率が良い

**デメリット**

- 全体実行時間が長い

### パターン 2: 非同期キューイング（オプション）

Pub/Sub を使用した非同期実行。

```
Controller → Pub/Sub (fetch-job)
                      ↓
            fetch-job → (メタデータ) → Pub/Sub (process-job)
                                              ↓
                                    process-job → (結果) → Pub/Sub (upload-job)
                                                                     ↓
                                                           upload-job → notify-job
```

**メリット**

- ジョブ間の疎結合
- スケーラビリティが高い

**デメリット**

- エラーハンドリング が複雑
- デバッグが困難

現在の実装はパターン 1（逐次実行）を前提としていますが、Pub/Sub を組み込む場合は Terraform の `trigger` モジュール設定を変更してください。

---

## ビルド・デプロイ手順

### 全ジョブをビルドしてプッシュ

```bash
PROJECT_ID="your-gcp-project"

# Controller
cd app/controller
docker build -t gcr.io/${PROJECT_ID}/controller:latest .
docker push gcr.io/${PROJECT_ID}/controller:latest

# fetch-job
cd ../fetch-job
docker build -t gcr.io/${PROJECT_ID}/fetch-job:latest .
docker push gcr.io/${PROJECT_ID}/fetch-job:latest

# process-job
cd ../process-job
docker build -t gcr.io/${PROJECT_ID}/process-job:latest .
docker push gcr.io/${PROJECT_ID}/process-job:latest

# upload-job
cd ../upload-job
docker build -t gcr.io/${PROJECT_ID}/upload-job:latest .
docker push gcr.io/${PROJECT_ID}/upload-job:latest

# notify-job
cd ../notify-job
docker build -t gcr.io/${PROJECT_ID}/notify-job:latest .
docker push gcr.io/${PROJECT_ID}/notify-job:latest

cd ..
```

### Terraform でデプロイ

`terraform/` で各ジョブのリソースを定義し、`terraform apply` でデプロイ。

例: `terraform/modules/compute/main.tf`

```hcl
# Controller (Cloud Run Service)
resource "google_cloud_run_service" "controller" {
  name     = "podcast-controller"
  location = var.region
  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/controller:latest"
      }
    }
  }
}

# fetch-job
resource "google_cloud_run_v2_job" "fetch_job" {
  name     = "fetch-job"
  location = var.region
  template {
    template {
      containers {
        image = "gcr.io/${var.project_id}/fetch-job:latest"
      }
    }
  }
}

# (その他のジョブも同様)
```

---

## トラブルシューティング

### ジョブが起動しない

- Cloud Run Jobs API が有効化されているか確認
- Service Account に適切な IAM ロールが付与されているか確認

### メモリ不足エラー

- Dockerfile で `--memory` フラグを設定（Terraform で `memory` を指定）
- 大きなファイルはストリーム処理に変更

### 認証エラー

- Service Account が Secret Manager にアクセス可能か確認
- Terraform で IAM ロール を付与

---

## 次のステップ

1. **Vertex AI 実装**: process-job で実際の Gemini API を呼び出す
2. **エラーハンドリング**: 各ジョブにリトライ・フォールバック処理を追加
3. **ユニットテスト**: 各ジョブのテストを追加
4. **監視・ロギング**: Cloud Logging / Cloud Trace の統合
