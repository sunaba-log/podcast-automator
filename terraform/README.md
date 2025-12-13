# terraform/

Terraform によるインフラ定義を一元管理するディレクトリです。

## ディレクトリ構成

```
terraform/
├── main.tf              # プロバイダ設定 (google, cloudflare等)
├── variables.tf         # 全体の変数定義 (Project ID, Region等)
├── outputs.tf           # 重要な出力値 (Bucket名, Service Account Email等)
├── backend.tf           # tfstateの保存先設定 (GCSバケット等)
├── terraform.tfvars     # 環境別の値(非VCS管理推奨)
│
└── modules/             # 再利用可能なリソース単位
    ├── core/            # 基本設定 (API有効化, Artifact Registry作成等)
    ├── storage/         # GCSバケット (Input用) & IAM
    ├── compute/         # Cloud Run Jobs & Service Account
    ├── trigger/         # Eventarc & Pub/Sub設定
    ├── ai/              # Vertex AI 関連 (IAM権限周り)
    └── secrets/         # Secret Manager (R2認証情報用)
```

## 使い方

### 初期化

```bash
cd terraform
terraform init
```

### 実行計画の確認

```bash
terraform plan -var-file="terraform.tfvars"
```

### 実装 (Apply)

```bash
terraform apply -var-file="terraform.tfvars"
```

### 環境変数

`terraform.tfvars` に以下を設定 (サンプル):

```hcl
project_id = "your-gcp-project"
region     = "asia-northeast1"
environment = "prod"
```

## 注意事項

- `terraform.tfvars` は `.gitignore` に追加して VCS 管理から外す
- tfstate は GCS に保存することを推奨（`backend.tf` で設定可能）
- Secret Manager のシークレット値（R2 キーなど）は Terraform 外で手動設定を推奨

## モジュール説明

- **core**: API 有効化、Artifact Registry、ロギング設定
- **storage**: Input/Output GCS バケット、ライフサイクル設定
- **compute**: Cloud Run Jobs、Service Account、IAM ロール
- **trigger**: Eventarc トリガー、Pub/Sub トピック
- **ai**: Vertex AI 権限設定
- **secrets**: Secret Manager シークレット基本設定

各モジュールは独立しており、必要に応じて有効化/無効化可能です。
