# Podcast Processor Agent (Cloud Run Job)

Google Cloud Run Jobs 上で動作するポッドキャスト配信自動化エージェントです。
GCS (Google Cloud Storage) にアップロードされた音声ファイルをトリガーに、AI による分析、Cloudflare R2 へのホスティング、RSS フィードの更新、Discord 通知までを一貫して実行します。

## ディレクトリ構成

```sh
.
├── main.py              # エントリーポイント (ワークフロー定義)
├── services/            # 各種サービスクラス
│   ├── ai_analyzer.py   # Vertex AI 連携
│   ├── r2_client.py     # Cloudflare R2 操作
│   ├── rss_manager.py   # RSSフィード生成・更新
│   └── ...
├── pyproject.toml       # 依存関係定義
├── uv.lock              # ロックファイル
└── Dockerfile           # コンテナ定義
```

## 🚀 主な機能

1.  **AI 分析 (Vertex AI / Gemini)**
    - 音声ファイル (GCS) を直接読み込み、文字起こしと要約（タイトル・概要）を自動生成します。
2.  **ホスティング (Cloudflare R2)**
    - 音声ファイルを GCS から配信用の R2 バケットへストリーム転送します（ローカルディスク消費なし）。
    - ファイルサイズと再生時間を自動計算します。
3.  **RSS フィード自動更新**
    - 既存の `feed.xml` を R2 から取得し、新エピソードを追加して再アップロードします。
4.  **通知 (Discord)**
    - 処理の進捗（開始・完了・エラー）を Discord Webhook で通知します。

## 📋 必要な環境

- **Google Cloud Platform**
  - Cloud Run Jobs
  - Vertex AI API (Gemini モデルの利用)
  - Cloud Storage (一時保存用)
  - Secret Manager (認証情報の管理)
- **Cloudflare**
  - R2 Storage (音声および RSS の公開用)
- **Python 3.12+**
  - パッケージ管理: `uv`

## ⚙️ 環境変数 (Environment Variables)

実行時に以下の環境変数を設定します。Cloud Run Job 実行時の `--set-env-vars` またはローカル実行時の `.env` で指定してください。

| 変数名                    | デフォルト値 / 例                      | 説明                                    |
| :------------------------ | :------------------------------------- | :-------------------------------------- |
| `PROJECT_ID`              | `taka-test-xxxx`                       | GCP プロジェクト ID                     |
| `GCS_BUCKET`              | **(必須)** `bucket`                    | 処理対象の音声ファイルのバケット名      |
| `GCS_TRIGGER_OBJECT_NAME` | **(必須)** `file.m4a`                  | 処理対象の音声ファイルのオブジェクト名  |
| `SECRET_NAME`             | `sunabalog-r2`                         | Secret Manager のシークレット名         |
| `R2_ENDPOINT_URL`         | `https://xxx.r2.cloudflarestorage.com` | Cloudflare R2 のエンドポイント          |
| `R2_BUCKET`               | `podcast`                              | R2 のバケット名                         |
| `SUBDIRECTORY`            | `test`                                 | R2 内の保存先サブディレクトリ           |
| `AI_MODEL_ID`             | `gemini-2.5-flash`                     | 使用する Vertex AI (Gemini) のモデル ID |
| `R2_CUSTOM_DOMAIN`        | `podcast.sunabalog.com`                | 配信用のカスタムドメイン                |

## 🔐 シークレット管理 (Google Secret Manager)

本アプリケーションは、機密情報を Google Secret Manager から取得します。
環境変数 `SECRET_NAME` で指定したシークレットに、以下の情報が含まれている必要があります（実装依存のため、JSON 形式などを想定）。

- Cloudflare R2 Access Key ID
- Cloudflare R2 Secret Access Key
- Discord Webhook URL

```json
{
  "r2_access_key": "<Cloudflare R2のアクセスキー>",
  "r2_secret_key": "<Cloudflare R2のシークレットキー>",
  "discord_webhook_url": "<Discord の webhook url>"
}
```

## 🛠️ ローカルでの実行方法

このプロジェクトはパッケージ管理に `uv` を使用しています。

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. gcloud login

```sh
gcloud auth application-default login
```

### 3. 実行

```sh
uv run main.py
```

## Cloudflare R2 におけるディレクトリ構造

**エピソード別**

「文字起こしテキスト(.txt)」や「チャプターファイル(.json)」など、1 エピソードあたりのファイル数が増える可能性あり

```markdown
podcast.sunabalog.com/
├── <channel_id>/
│ ├── feed.xml
│ ├── artwork.jpg
│ └── ep/
│ ├── <number>/ # エピソードごとにディレクトリを切る
│ │ ├── audio.mp3 # ファイル名を固定できるメリットあり
│ │ ├── cover.jpg
│ │ └── transcript.txt # 将来的な拡張
│ └── <number_2>/
│ ├── audio.mp3
│ └── cover.jpg
```

## インフラ側の事前準備

### Cloudflare R2 に RSS フィードを追加

`{BUCKET_NAME}/{SUBDIRECTORY}/feed.xml`を作成する。

**RSS フィードを新規作成する場合：**

```python
from services import PodcastRssManager

generator = PodcastRssManager()
rss_feed = generator.generate_podcast_rss(
    title=PODCAST_TITLE,
    description=PODCAST_DESCRIPTION,
    language=PODCAST_LANGUAGE,
    category=PODCAST_CATEGORY,
    cover_url=PODCAST_COVER_URL,
    owner_name=PODCAST_OWNER_NAME,
    owner_email=PODCAST_OWNER_EMAIL,
    author=PODCAST_AUTHOR,
    copyright_text=PODCAST_COPYRIGHT,
)

with open("feed.xml", "w", encoding="utf-8") as f:
    f.write(rss_feed)
```

### GCP Secret Manager にシークレット作成

```json
{
  "r2_access_key": "<Cloudflare R2のアクセスキー>",
  "r2_secret_key": "<Cloudflare R2のシークレットキー>",
  "discord_webhook_url": "<Discord のs webhook url>"
}
```

### GCP Cloud Run Job の環境変数を構成

[ジョブの環境変数を構成する](https://docs.cloud.google.com/run/docs/configuring/jobs/environment-variables?hl=ja)

```env
PROJECT_ID=<Google Cloud のプロジェクト ID>
SECRET_NAME=<Google Cloud Secret Managerで管理しているシークレット名, i.e. "podcast-automator">
GCS_BUCKET=<処理対象の音声ファイルのバケット名>
GCS_TRIGGER_OBJECT_NAME=<処理対象の音声ファイルのオブジェクト名>
R2_ENDPOINT_URL=<Cloudflare R2のURL, default:"https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com">
R2_BUCKET_=<cloudflare R2のバケット名, default: "podcast">
SUBDIRECTORY=<R2内の保存先フォルダ, default: "test">
AUDIO_FILE_URL=<GCSにアップロードされたmp3,m4aファイルパス, default: "gs://sample-audio-for-sunabalog/
AI_MODEL_ID=<GeminiモデルID, default:"gemini-2.5-flash">
R2_CUSTOM_DOMAIN=<R2のカスタムドメイン, default: "podcast.sunabalog.com">
```

## テスト

### ローカルで検証

#### 1. gcloud login

```sh
gcloud auth application-default login
```

#### 2. docker build

```sh
docker build -t podcast-automator-job:latest .
```

#### 3. docker run

```sh
docker run -v ~/.config/gcloud/application_default_credentials.json:/tmp/keys/adc.json:ro \
-e PROJECT_ID=taka-test-481815 \
-e SECRET_NAME=podcast-automator \
-e GCS_BUCKET=sample-audio-for-sunabalog  \
-e GCS_TRIGGER_OBJECT_NAME=short_dialogue.m4a \
-e R2_ENDPOINT_URL=https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com \
-e R2_BUCKET=podcast \
-e SUBDIRECTORY=test \
-e AI_MODEL_ID=gemini-2.5-flash \
-e R2_CUSTOM_DOMAIN=podcast.sunabalog.com  \
-e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/adc.json \
-e GOOGLE_CLOUD_PROJECT=taka-test-481815 \
podcast-automator-job:latest
```
