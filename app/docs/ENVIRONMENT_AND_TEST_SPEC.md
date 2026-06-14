# Environment and Test Specification

このドキュメントは、アプリ実行時の環境変数仕様とテスト実行ポリシーを定義します。

## 1. Runtime Profiles

本アプリには次の実行プロファイルがあります。

- Podcast Processing Job
  - entrypoint: src/entrypoints/main.py
  - usecase: src/usecases/process_podcast_workflow.py
- Weekly Agenda Job
  - entrypoint: src/entrypoints/agenda_main.py
  - usecase: src/usecases/generate_weekly_agenda.py

## 2. Environment Variables

### 2.1 Podcast Processing Job

| Name | Required | Default | Description |
| --- | --- | --- | --- |
| PROJECT_ID | Yes | - | GCP project ID |
| GCS_BUCKET | Yes | - | Input audio bucket |
| GCS_TRIGGER_OBJECT_NAME | Yes | - | Input audio object path |
| R2_BUCKET | Yes | - | Cloudflare R2 bucket |
| SECRET_NAME | Conditional | - | Secret Manager secret name |
| CLOUDFLARE_ACCESS_KEY_ID | Conditional | - | R2 access key (when SECRET_NAME is not used) |
| CLOUDFLARE_SECRET_ACCESS_KEY | Conditional | - | R2 secret key (when SECRET_NAME is not used) |
| CLOUDFLARE_ACCOUNT_ID | No | 8ed20f6872cea7c9219d68bfcf5f98ae | Used to derive R2 endpoint |
| R2_ENDPOINT_URL | No | https://<CLOUDFLARE_ACCOUNT_ID>.r2.cloudflarestorage.com | Explicit R2 endpoint override |
| R2_KEY_PREFIX | No | test | Key prefix under bucket |
| DISCORD_WEBHOOK_INFO_URL | No | - | Discord webhook URL for notifications |
| AI_MODEL_ID | No | gemini-2.5-flash | Gemini model ID |
| R2_CUSTOM_DOMAIN | No | podcast.sunabalog.com | Public domain for generated audio URL |

Conditional rule:

- SECRET_NAME を指定しない場合、CLOUDFLARE_ACCESS_KEY_ID と CLOUDFLARE_SECRET_ACCESS_KEY の両方が必要です。

### 2.2 Weekly Agenda Job

| Name | Required | Default | Description |
| --- | --- | --- | --- |
| DISCORD_WEBHOOK_AGENDA_URL | Yes | - | Weekly agenda post destination |
| DISCORD_BOT_TOKEN | No | - | Discord API token for transcript fetching |
| DISCORD_TRANSCRIPT_CHANNEL_ID | No | - | Source channel ID for transcript messages |
| TRANSCRIPT_FETCH_LIMIT | No | 50 | Number of messages to fetch |
| DEBUG_JSON_PATH | No | - | Optional path to dump AgendaResult JSON |
| GOOGLE_CLOUD_PROJECT | No | - | Required only when AI news research is enabled |

Behavior rule:

- DISCORD_BOT_TOKEN または DISCORD_TRANSCRIPT_CHANNEL_ID が未設定の場合、transcript 解析をスキップして固定メッセージで通知します。

## 3. Secret Manager Contract

Podcast Processing Job で SECRET_NAME を使う場合、シークレットは次のキーを持つ JSON を想定します。

```json
{
  "r2_access_key": "<Cloudflare R2 access key>",
  "r2_secret_key": "<Cloudflare R2 secret key>",
  "discord_webhook_url": "<Discord webhook URL>"
}
```

## 4. Test Profiles

### 4.1 Default test profile

- Command: make test
- Actual command: uv run pytest --cov=. tests
- Note: pyproject.toml の addopts により一部テストを除外します。

Current default exclusions:

- tests/test_storage.py
- tests/test_ai_analyzer.py
- tests/test_get_audio_info.py

### 4.2 Full test profile

- Command: uv run pytest --cov=. tests -o addopts=''
- Purpose: addopts による除外を無効化して全テスト実行

### 4.3 Lint profile

- Command: make lint
- Includes:
  - ruff check
  - ruff format --check
  - uv pip check

## 5. CI/Local Operation Guidelines

- ローカルで仕様変更した場合は、最低限次を確認すること。
  - make lint
  - make test
- エントリーポイントや外部連携周りを変更した場合は、次も実行すること。
  - uv run pytest --cov=. tests -o addopts=''
- 環境変数の追加・変更時は次の 2 ファイルを同時更新すること。
  - .env.sample
  - README.md
