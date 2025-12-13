# Deployment Guide

このガイドは、`terraform/` を使用してシステムを GCP にデプロイするための手順です。

## 前提条件

- GCP プロジェクトが既に作成されている
- `gcloud` CLI がインストール・認証済み
- Terraform 1.0 以上
- Cloud Run Jobs API が有効化されている（`terraform/modules/core` が自動で行う）

## ステップ 1: 環境変数・変数を設定

`terraform/` ディレクトリに移動し、`terraform.tfvars` を作成：

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` を編集して以下を設定：

```hcl
project_id           = "your-gcp-project-id"
region               = "asia-northeast1"
environment          = "dev"
service_name         = "podcast-processor"
input_bucket_name    = "podcast-input-dev"
output_bucket_name   = "podcast-output-dev"
container_image      = "gcr.io/your-gcp-project-id/podcast-processor:latest"
cloudflare_api_token = "your-cloudflare-api-token"  # 後で設定可能
cloudflare_account_id = "your-cloudflare-account-id"
```

## ステップ 2: gcloud でプロジェクトを認証

```bash
gcloud auth login
gcloud config set project <your-project-id>
```

## ステップ 3: tfstate 保存用 GCS バケットを作成（バックエンド設定用）

```bash
gsutil mb gs://podcast-automator-tfstate
gsutil versioning set on gs://podcast-automator-tfstate
```

## ステップ 4: Terraform を初期化

```bash
terraform init \
  -backend-config="bucket=podcast-automator-tfstate" \
  -backend-config="prefix=podcast-automator"
```

## ステップ 5: コンテナイメージをビルド・プッシュ

Cloud Run Jobs で使用するコンテナイメージを、Artifact Registry にプッシュしておく必要があります。

```bash
# リポジトリのルートに戻る
cd ..

# イメージをビルド
docker build -t gcr.io/your-gcp-project-id/podcast-processor:latest ./app/worker

# Artifact Registry にプッシュ
docker push gcr.io/your-gcp-project-id/podcast-processor:latest
```

（もし GCR（Google Container Registry）を使う場合：）

```bash
docker build -t gcr.io/<project-id>/podcast-processor:latest ./app/worker
docker push gcr.io/<project-id>/podcast-processor:latest
```

## ステップ 6: Terraform Plan で確認

```bash
cd terraform
terraform plan -var-file="terraform.tfvars"
```

## ステップ 7: Terraform Apply でデプロイ

```bash
terraform apply -var-file="terraform.tfvars"
```

確認プロンプトで `yes` と入力。

## ステップ 8: Secret Manager にシークレットを登録

Terraform が Secret Manager リソースを作成したら、シークレット値を手動で登録：

### R2 認証情報

```bash
gcloud secret versions add cloudflare-r2-keys --data-file=- << 'EOF'
{
  "access_key_id": "your-r2-access-key",
  "secret_access_key": "your-r2-secret-key",
  "bucket": "your-r2-bucket",
  "endpoint_url": "https://<account-id>.r2.cloudflarestorage.com"
}
EOF
```

### Discord Webhook URL

```bash
gcloud secret versions add discord-webhook-url --data-file=- << 'EOF'
https://discordapp.com/api/webhooks/xxxxx/yyyyy
EOF
```

## ステップ 9: 出力値を確認

```bash
terraform output
```

重要な出力：

- `input_bucket_name` - 音声ファイルのアップロード先
- `service_account_email` - Cloud Run Jobs のサービスアカウント
- `cloud_run_job_name` - デプロイされたジョブ名

## ステップ 10: 動作確認（ローカルテスト）

Cloud Run Jobs を手動実行してテスト：

```bash
gcloud run jobs execute podcast-processor \
  --region asia-northeast1
```

ログを確認：

```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=podcast-processor" \
  --limit 50 --format json
```

## ステップ 11: Eventarc トリガーの確認

Eventarc トリガーが GCS オブジェクト作成時に Cloud Run Job を起動するか確認：

```bash
# GCS に音声ファイルをアップロード
gsutil cp test-sample.mp3 gs://podcast-input-dev/

# Cloud Run Job のログを確認
gcloud logging read "resource.type=cloud_run_job" \
  --limit 50 --format json
```

## 環境の削除（本番環境では注意！）

```bash
terraform destroy -var-file="terraform.tfvars"
```

## トラブルシューティング

### エラー: `The run service does not exist`

Cloud Run API が有効化されていない可能性があります。以下を確認：

```bash
gcloud services enable run.googleapis.com
```

### エラー: `Permission denied: Could not delete bucket`

GCS バケットが空でないか、削除保護が有効の可能性があります。

### Container Image Pull エラー

イメージが Artifact Registry / GCR に存在するか確認：

```bash
gcloud container images list
gcloud container images describe gcr.io/<project-id>/podcast-processor:latest
```

## 本番環境への展開

1. 環境ごとに `terraform.tfvars` ファイルを分離（`prod.tfvars` など）
2. 状態ファイルを環境ごとに分ける（バックエンド設定で prefix を変更）
3. リソースの削除保護を有効化（`prevent_destroy = true`）
4. 自動バックアップの有効化
5. CloudTrail / Cloud Audit Logs でアクティビティを監視
