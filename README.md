# podcast-automator

このリポジトリは、GCP 上で **GCS への音声アップロード → Eventarc → Workflows → Cloud Run Jobs** の起動までを Terraform で構成するためのコードと、
Cloud Run Jobs で実行される **テスト用の簡易 Python アプリ**（GCS → Cloudflare R2 転送と Discord 通知のみ）を含みます。

**重要**: 現時点の `app/src/main.py` はテスト用に適当に作ったものです。
音声処理や RSS 更新などは実装しておらず、GCS から R2 へ転送するだけです。
実装済みの構成は `ARCHITECTURE.md` を参照してください。

## 構成

```
.
├── app/                         # Python アプリ (Cloud Run Job 用)
│   ├── src/main.py              # GCS → R2 転送 + Discord 通知
│   ├── tests/                   # pytest
│   ├── pyproject.toml           # Python 3.12 / ruff / pytest 設定
│   └── Dockerfile               # Cloud Run Job 用イメージ
├── infrastructure/              # Terraform (GCP リソース)
│   ├── *.tf                     # バケット, Eventarc, Workflows, IAM 等
│   ├── environments/            # dev/prod の backend/variables
│   └── modules/                 # Artifact Registry / Cloud Run Job modules
├── .github/workflows/           # CI/CD
├── .devcontainer/               # Dev Container 設定 (注意事項あり)
```

## 現状のアプリ挙動

`app/src/main.py` は次の動作のみを行います。

- `DISCORD_WEBHOOK_INFO_URL` があれば、開始・終了メッセージを送信
- `GCS_TRIGGER_OBJECT_NAME` で指定された GCS オブジェクトを Cloudflare R2 に転送
- 失敗時は `DISCORD_WEBHOOK_ERROR_URL` があればエラーメッセージを送信

## ローカル開発 (app)

前提: Python 3.12+ と `uv` が必要です（`app/pyproject.toml` で指定）。

```bash
cd app
make install
make lint
make test
```

Docker ビルド:

```bash
make docker-build
```

## インフラ (Terraform)

Terraform は Docker コンテナで実行する前提です。`Makefile` が用意されています。
`.env.sample` に `GOOGLE_APPLICATION_CREDENTIALS` と Cloudflare 認証情報の例があります。
ローカルからデプロイする場合は、サービスアカウントの JSON を配置し、そのパスを `.env` の `GOOGLE_APPLICATION_CREDENTIALS` に設定してください。
あわせて Cloudflare の認証情報（`CLOUDFLARE_ACCESS_KEY_ID` / `CLOUDFLARE_SECRET_ACCESS_KEY` / `CLOUDFLARE_API_TOKEN`）も `.env` に設定してください。

### デプロイ手段

- GitHub Actions の CD (`.github/workflows/cd.yml`) からデプロイ
  - `develop` / `main` への push で自動実行
  - `workflow_dispatch` でブランチ指定デプロイ
- ローカルから `make terraform-deploy-{dev,prod}` でデプロイ
  - ローカル実行時は、サービスアカウントの JSON を配置し、そのパスを `.env` の `GOOGLE_APPLICATION_CREDENTIALS` に設定してください
  - あわせて Cloudflare の認証情報も `.env` に設定してください

```bash
# 例: dev 環境のデプロイ
make terraform-deploy-dev DEPLOY_COMMAND_EXTENSION="-auto-approve"
```

環境別設定は `infrastructure/environments/{dev,prod}` にあります。

## GitHub Actions

- `CI` (`.github/workflows/ci.yml`)
  - app: uv + ruff + pytest
  - infrastructure: Terraform fmt チェック（`fmt -check`）+ validate
- `CD` (`.github/workflows/cd.yml`)
  - `develop` と `main` で自動デプロイ
  - `workflow_dispatch` でブランチ指定デプロイ

## ブランチルール

### マージフロー

- `main` <- `release/YYYYMMDD`, `hotfix/*`
- `release/YYYYMMDD` <- `develop`
- `develop` <- `feature/XXX`, `epic/YYY`
- `epic/YYY` <- `feature/ZZZ`

`XXX` と `YYY` は issue 番号、`ZZZ` は sub-issue 番号です。

#### 補足

- `main` への PR は `release/YYYYMMDD` または `hotfix/*` からのみ許可する
- `develop` からその日の日付で `release/YYYYMMDD` を作成し、`main` へ PR する
- `develop` から各 issue の `epic/YYY` または `feature/XXX` / `fix/XXX` を作成する
  - sub-issue がある issue は `epic/YYY`（親）
  - sub-issue がない issue は `feature/XXX` または `fix/XXX`（単独）
- `epic/YYY` から sub-issue に対応する `feature/ZZZ` を作成し、`epic/YYY` へ PR する

### 運用ルール

- PR 必須（直 push 禁止）
- issue / sub-issue と PR は 1 対 1
- `main` へのマージはレビュー必須

## 環境変数 (app)

`app/.env.sample` に記載されています。

```
GCS_BUCKET=your-input-bucket-name
GCS_TRIGGER_OBJECT_NAME=path/to/input/file.mp3
DISCORD_WEBHOOK_INFO_URL=https://discord.example/webhook/info
DISCORD_WEBHOOK_ERROR_URL=https://discord.example/webhook/error
R2_BUCKET=your-r2-bucket-name
CLOUDFLARE_ACCOUNT_ID=your-cloudflare-account-id
CLOUDFLARE_ACCESS_KEY_ID=your-cloudflare-access-key-id
CLOUDFLARE_SECRET_ACCESS_KEY=your-cloudflare-secret-access-key
```

## Dev Container について

手をつけていないため使うには要修正
