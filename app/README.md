# Podcast Automator App

Cloud Run Jobs 上で動作するポッドキャスト配信自動化アプリです。現行実装は次の 2 つのジョブで構成されています。

- Podcast Processing Job: GCS 音声を文字起こし・要約し、R2 配信と RSS 更新、Discord 通知まで実行
- Weekly Agenda Job: Discord の transcript から収録アジェンダを生成し、Discord 通知

## アーキテクチャ概要

DDD 構成に段階移行済みです。レイヤ責務は次の通りです。

- entrypoints: 実行時の環境変数解決とユースケース起動
- usecases: アプリケーションフローのオーケストレーション
- infrastructure: 外部 I/O アダプタ（GCP/Cloudflare/Discord/Gemini）
- domain: モデルとポート（interfaces）
- services: ドメイン寄りの処理ロジック（整形・解析・ニュース抽出など）

主要エントリーポイント:

- src/entrypoints/main.py
- src/entrypoints/agenda_main.py

互換ラッパー:

- src/main.py
- src/agenda_main.py

## ディレクトリ構成

```text
app/
├── src/
│   ├── domain/
│   │   ├── interfaces/
│   │   └── models/
│   ├── entrypoints/
│   │   ├── main.py
│   │   └── agenda_main.py
│   ├── infrastructure/
│   │   ├── ai_analyzer.py
│   │   ├── discord_fetcher.py
│   │   ├── notifier.py
│   │   ├── secret_manager.py
│   │   └── storage.py
│   ├── services/
│   │   ├── agenda_formatter.py
│   │   ├── audio_converter.py
│   │   ├── news_fetcher.py
│   │   ├── news_relevance.py
│   │   ├── news_researcher.py
│   │   ├── rss_manager.py
│   │   └── transcript_analyzer.py
│   └── usecases/
│       ├── process_podcast_workflow.py
│       └── generate_weekly_agenda.py
├── tests/
├── examples/
├── docs/
├── pyproject.toml
├── Makefile
└── Dockerfile
```

## セットアップ

### 前提

- Python 3.12+
- uv
- gcloud CLI（実 API 実行時のみ）

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. 認証

実 API を叩く場合のみ実施します。

```bash
gcloud auth application-default login
```

### 3. 環境変数

```bash
cp .env.sample .env
```

変数仕様は docs/ENVIRONMENT_AND_TEST_SPEC.md を参照してください。

Podcast Processing Jobでは、`DATABASE_URL`でCloud SQLへ接続します。Cloud Run Jobでは
Cloud SQL Unix socketを`/cloudsql`へマウントし、GCSオブジェクトパスから取得した
`podcast_id` / `episode_id`で処理状態を更新します。

### GCS アップロードパスの規約

音声ファイルを処理対象のGCSバケットにアップロードする際は、以下のパス規則に従う必要があります。

```text
podcasts/{podcast_id}/episodes/{episode_id}/source/{filename}.{mp3|m4a|wav|flac}
```

- `{podcast_id}` および `{episode_id}` には、1以上の整数値（数字）を指定してください。
- 拡張子は、`.mp3`, `.m4a`, `.wav`, `.flac`（大文字小文字不問）のいずれかである必要があります。
- 音声ファイルがこのパス形式でアップロードされると、システム内部で自動的に `podcast_id` と `episode_id` がパースされ、Cloud SQL（PostgreSQL）やFirestoreの処理状態更新やデータ保存時の共通キーとして使用されます。

## 実行方法

### Podcast Processing Job

```bash
uv run python -m entrypoints.main
```

または互換ラッパー:

```bash
uv run python -m main
```

### Weekly Agenda Job

```bash
uv run python -m entrypoints.agenda_main
```

または互換ラッパー:

```bash
uv run python -m agenda_main
```

## テストと品質チェック

### Lint

```bash
make lint
```

### 通常テスト

`pyproject.toml` の `addopts` により一部テストを除外して実行します。

```bash
make test
```

### フルテスト（除外なし）

```bash
uv run pytest --cov=. tests -o addopts=''
```

### よく使うピンポイント実行

```bash
uv run pytest tests/test_ai_analyzer.py -q -o addopts=''
uv run pytest tests/test_news_researcher.py -q -o addopts=''
uv run pytest tests/test_main.py tests/test_notifier.py tests/test_discord_fetcher.py -q -o addopts=''
```

## Docker ビルド

```bash
make docker-build
```

## 補助仕様書

- docs/ENVIRONMENT_AND_TEST_SPEC.md

この仕様書に以下をまとめています。

- ジョブ別の環境変数仕様（必須/任意/デフォルト/備考）
- Secret Manager の想定 JSON 形式
- テストプロファイル（通常/フル）と運用ルール
