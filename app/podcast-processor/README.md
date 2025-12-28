## ディレクトリ構造 \*Cloudflare R2 における

### エピソード別

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

## 事前準備

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
R2_ENDPOINT_URL=<Cloudflare R2のURL, default:"https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com">
BUCKET_NAME=<cloudflare R2のバケット名, default: "podcast">
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
-e R2_ENDPOINT_URL=https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com \
-e BUCKET_NAME=podcast \
-e SUBDIRECTORY=test \
-e AUDIO_FILE_URL=gs://sample-audio-for-sunabalog/short_dialogue.m4a \
-e AI_MODEL_ID=gemini-2.5-flash \
-e R2_CUSTOM_DOMAIN=podcast.sunabalog.com  \
-e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/adc.json \
-e GOOGLE_CLOUD_PROJECT=taka-test-481815 \
podcast-automator-job:latest
```

## 参考

- [Directory>R2>Examples>S3 SDKs>boto3](https://developers.cloudflare.com/r2/examples/aws/boto3/)
