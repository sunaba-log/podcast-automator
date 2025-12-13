# podcast-automator

GCP (Cloud Run Jobs) と Cloudflare R2 を使用したポッドキャスト自動処理システムの実装テンプレートです。

## ディレクトリ構成

```
.
├── app/                     # アプリケーションコード (Cloud Run Jobs用)
│   ├── controller/          # ジョブ制御コンポーネント
│   │   ├── main.py          # ジョブコントローラー
│   │   ├── Dockerfile       # コンテナイメージ定義
│   │   └── requirements.txt  # Python 依存パッケージ
│   │
│   ├── fetch-job/           # ポッドキャスト取得ジョブ
│   │   ├── main.py          # 取得処理
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/           # ユニットテスト
│   │
│   ├── process-job/         # ポッドキャスト処理ジョブ (Vertex AI)
│   │   ├── main.py          # 処理ロジック (Gemini 1.5 Pro)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/           # ユニットテスト
│   │
│   ├── upload-job/          # ファイルアップロードジョブ
│   │   ├── main.py          # R2 アップロード処理
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── notify-job/          # 通知ジョブ
│   │   ├── main.py          # Discord/メール通知
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── shared/              # 共有ユーティリティ
│       ├── __init__.py
│       ├── ai.py            # Vertex AI API 呼び出し
│       ├── cdn.py           # Cloudflare R2 (S3互換) 操作
│       ├── config.py        # 設定管理
│       ├── logger.py        # ロギング
│       ├── models.py        # データモデル
│       ├── notifier.py      # 通知機能
│       ├── storage.py       # GCS 操作
│       ├── pyproject.toml   # Python パッケージ定義
│       └── README.md
│
├── terraform/               # インフラ定義 (IaC)
│   ├── main.tf              # プロバイダ・モジュール呼び出し
│   ├── variables.tf         # 全体変数定義
│   ├── outputs.tf           # 出力値定義
│   ├── backend.tf           # tfstate保存先設定
│   ├── terraform.tfvars.example
│   └── modules/             # 再利用可能なTerraformモジュール
│       ├── core/            # API有効化、Artifact Registry
│       ├── storage/         # GCS バケット管理
│       ├── compute/         # Cloud Run Jobs & Service Account
│       ├── trigger/         # Eventarc & Pub/Sub
│       ├── ai/              # Vertex AI IAM
│       └── secrets/         # Secret Manager
│
├── pyproject.toml           # プロジェクト全体の Python 設定
├── pytest.ini               # pytest 設定
├── Makefile                 # ビルド・デプロイ用コマンド
├── DEPLOYMENT.md            # デプロイメント手順
├── JOB_ARCHITECTURE.md      # ジョブアーキテクチャ設計
├── DEVCONTAINER_QUICKSTART.md # Dev Container クイックスタート
└── README.md                # このファイル
```

## システム構成

```
配信者
  ↓ (mp3)
GCS Input Bucket
  ↓ (Eventarc)
Cloud Run Job (controller)
  ├── fetch-job   → ポッドキャストメタデータ取得
  ├── process-job → Vertex AI (Gemini 1.5 Pro) で処理
  ├── upload-job  → Cloudflare R2 にアップロード
  └── notify-job  → Discord/Email 通知
  ↓
Cloudflare R2 (CDN)
  ↓
Podcast RSS フィード配信
```

## ワークフロー

1. **配信者**が音声ファイル (.mp3) を **GCS Input Bucket** にアップロード

2. **Eventarc** が Object Finalize イベントを検知し、**controller** を起動

3. **controller** が各ジョブを順序管理：

   - **fetch-job**: ポッドキャスト情報を GCS から取得
   
   - **process-job**: 以下の処理を実行
     - GCS から音声ファイルをダウンロード
     - **Vertex AI (Gemini 1.5 Pro)** に送信してタイトル・概要・議事録を生成
     - メタデータを JSON で保存
   
   - **upload-job**: 処理済みファイルを **Cloudflare R2** にアップロード
   
   - **notify-job**: 処理完了を **Discord/Email** で通知

4. **Podcast アプリ**が R2 の RSS フィード経由で配信を開始

## クイックスタート

### 前提条件

- Docker & Docker Compose
- Python 3.11+
- GCP アカウント & `gcloud` CLI
- Terraform 1.6+

### 1. Dev Container での開発環境構築

```bash
# VS Code で Dev Container を再度開く
# または以下を手動で実行

bash .devcontainer/post-create.sh
```

### 2. 各ジョブのコンテナイメージをビルド

```bash
# Make コマンド使用（推奨）
make build

# または手動でビルド
docker build -t podcast-controller:latest app/controller/
docker build -t podcast-fetch-job:latest app/fetch-job/
docker build -t podcast-process-job:latest app/process-job/
docker build -t podcast-upload-job:latest app/upload-job/
docker build -t podcast-notify-job:latest app/notify-job/
```

### 3. ローカルテスト

```bash
# 全テストを実行
pytest app/ -v --cov=app/shared

# 特定ジョブのみテスト
pytest app/fetch-job/tests/ -v
pytest app/process-job/tests/ -v

# コード整形
black app/
ruff check app/ --fix
```

### 4. GCP へのデプロイ

詳細は [DEPLOYMENT.md](./DEPLOYMENT.md) を参照：

```bash
# Terraform 初期化
cd terraform
terraform init

# デプロイ前確認
terraform plan -var-file="terraform.tfvars"

# デプロイ実行
terraform apply -var-file="terraform.tfvars"
```

## 機能モジュール

### app/shared/ - 共有ユーティリティ

- **config.py** - 環境変数・設定管理
- **logger.py** - 構造化ログ & Cloud Logging 連携
- **storage.py** - GCS ファイルダウンロード/アップロード
- **cdn.py** - Cloudflare R2 (S3 互換) 操作
- **ai.py** - Vertex AI (Gemini 1.5 Pro) API 呼び出し
- **models.py** - データモデル (Podcast, Episode など)
- **notifier.py** - Discord/Email 通知

### app/*/main.py - 各ジョブの処理

- **controller/main.py** - ジョブ制御・オーケストレーション
- **fetch-job/main.py** - ポッドキャスト情報取得
- **process-job/main.py** - AI による処理（テキスト生成）
- **upload-job/main.py** - R2 へのアップロード
- **notify-job/main.py** - 通知送信

### terraform/modules/

- **core** - API 有効化、Artifact Registry 作成
- **storage** - GCS バケット、ライフサイクル設定
- **compute** - Cloud Run Jobs & Service Account
- **trigger** - Eventarc トリガー、Pub/Sub トピック
- **ai** - Vertex AI IAM 権限
- **secrets** - Secret Manager リソース定義

## 環境変数・シークレット

### アプリケーション (Cloud Run Jobs)

Environment Variables:

- `ENVIRONMENT` - dev / staging / prod
- `PROJECT_ID` - GCP Project ID
- `GCP_REGION` - GCP リージョン (デフォルト: asia-northeast1)
- `INPUT_BUCKET` - 入力 GCS バケット名
- `OUTPUT_BUCKET` - 出力 GCS バケット名
- `LOG_LEVEL` - ログレベル (DEBUG/INFO/WARNING/ERROR)

Secret Manager (GCP):

- `r2-access-key` - Cloudflare R2 アクセスキー
- `r2-secret-key` - Cloudflare R2 シークレットキー
- `discord-webhook-url` - Discord Webhook URL
- `vertex-ai-project-id` - Vertex AI プロジェクト ID

### Terraform

`terraform/terraform.tfvars` (例):

```hcl
project_id           = "your-gcp-project"
region               = "asia-northeast1"
environment          = "dev"
input_bucket_name    = "podcast-input-dev"
output_bucket_name   = "podcast-output-dev"
artifact_registry    = "gcr.io/your-project"
cloudflare_api_token = "your-api-token"
```

## セキュリティに関する注意

- **本番環境では必須：**
  - `terraform.tfvars` を `.gitignore` に追加（シークレット未含）
  - シークレット値を Secret Manager で管理
  - Service Account に最小限の IAM ロールを付与
  - 監査ログを Cloud Logging で監視
  - tfstate をリモート (GCS) に保存し、リクエスト検証を有効化

## 本番環境への準備

### 必須実装項目

- ✅ エラーハンドリング・リトライ戦略の強化
- ✅ Cloud Logging による構造化ログ
- ✅ Cloud Trace・Cloud Profiler 統合
- ✅ ユニットテスト・統合テスト
- ✅ Cloud Monitoring・Cloud Alerting 設定
- ✅ CI/CD パイプライン (Cloud Build)
- ✅ セキュリティ監査・コンプライアンスチェック

### セキュリティベストプラクティス

- **シークレット管理**: Secret Manager 使用、tfstate は暗号化・リモート保存
- **IAM**: Service Account に最小限の権限付与、定期的な監査
- **ネットワーク**: VPC・Private IP 使用、アクセス制御の厳格化
- **暗号化**: 保存時・転送時とも暗号化を有効化
- **監査ログ**: Cloud Audit Logs による全操作の記録

## ドキュメント

- [JOB_ARCHITECTURE.md](./JOB_ARCHITECTURE.md) - ジョブアーキテクチャの詳細設計
- [DEPLOYMENT.md](./DEPLOYMENT.md) - GCP へのデプロイメント手順
- [DEVCONTAINER_QUICKSTART.md](./DEVCONTAINER_QUICKSTART.md) - Dev Container セットアップ
- [app/shared/README.md](./app/shared/README.md) - 共有モジュール API ドキュメント

## 参考リソース

- [Cloud Run Jobs ドキュメント](https://cloud.google.com/run/docs/quickstarts/jobs)
- [Eventarc ドキュメント](https://cloud.google.com/eventarc/docs)
- [Vertex AI API リファレンス](https://cloud.google.com/python/docs/reference/aiplatform/latest)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [pytest ドキュメント](https://docs.pytest.org/)
- [Docker ドキュメント](https://docs.docker.com/)

## ライセンス

MIT (LICENSE ファイル参照)
