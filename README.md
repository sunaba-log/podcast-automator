# podcast-automator

このリポジトリは、GCP 上で **GCS への音声アップロード → Eventarc → Workflows → Cloud Run Jobs** の起動までを Terraform で構成するためのコードと、
Cloud Run Jobs で実行される Python アプリを含みます。

現行の app は以下を実装済みです。

- GCS 音声の文字起こし・要約（Gemini）
- Cloudflare R2 へのアップロード
- RSS フィード更新
- Discord 通知
- Discord transcript からの週次アジェンダ生成

実装済みの構成は ARCHITECTURE.md と app/README.md を参照してください。

## 構成

```
.
├── app/                         # Python アプリ (Cloud Run Job 用)
│   ├── src/entrypoints/         # 実行エントリーポイント
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

アプリの実行モードは 2 つです。

- Podcast Processing Job
  - entrypoint: app/src/entrypoints/main.py
  - 音声文字起こし、要約、R2 配信、RSS 更新、Discord 通知
- Weekly Agenda Job
  - entrypoint: app/src/entrypoints/agenda_main.py
  - Discord transcript 解析、ニュース候補抽出、アジェンダ投稿

詳細な環境変数やテスト手順は app/README.md を参照してください。

## ローカル開発 (app)

前提: Python 3.12+ と `uv` が必要です（`app/pyproject.toml` で指定）。

```bash
cd app
make install
make lint
make test
```

フルテスト（除外なし）:

```bash
uv run pytest --cov=. tests -o addopts=''
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

最新の環境変数定義は以下を参照してください。

- app/.env.sample
- app/README.md
- app/docs/ENVIRONMENT_AND_TEST_SPEC.md

## Dev Container について

手をつけていないため使うには要修正
