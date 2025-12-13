# app/

Cloud Run Jobs ごとにモジュール化されたジョブのソースコード。

## ディレクトリ構成

```
app/
├── controller/                   # Cloud Run Service (HTTP受信・Job起調)
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── fetch-job/                    # Cloud Run Job (GCS ダウンロード)
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── process-job/                  # Cloud Run Job (Vertex AI処理)
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── upload-job/                   # Cloud Run Job (R2アップロード)
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── notify-job/                   # Cloud Run Job (Discord通知)
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
└── shared/                       # 共有ライブラリ
    ├── __init__.py
    ├── config.py                 # 設定・環境変数
    ├── storage.py                # GCS操作
    ├── ai.py                     # Vertex AI操作
    ├── cdn.py                    # Cloudflare R2操作
    ├── notifier.py               # Discord通知
    ├── logger.py                 # ロギング
    └── models.py                 # 共有データモデル
```

## ジョブ間のデータフロー

```
Event (GCS Object Finalize)
         ↓
    Controller (Service)
    - イベント受け取り
    - ジョブ入力を Pub/Sub / Datastore へ保存
         ↓
    fetch-job (Job)
    - GCS から mp3 をダウンロード
    - 一時ストレージ / GCS に保存
         ↓
    process-job (Job)
    - Vertex AI に音声送信
    - メタデータ生成（タイトル・概要・議事録）
         ↓
    upload-job (Job)
    - メタデータ + 音声を R2 にアップロード
    - RSS を生成・公開
         ↓
    notify-job (Job)
    - 完了/失敗を Discord に通知
```

## 各モジュールの責務

| モジュール      | 役割                    | 入力              | 出力               |
| --------------- | ----------------------- | ----------------- | ------------------ |
| **controller**  | HTTP 受け取り・Job 起動 | Eventarc イベント | Job 起動コマンド   |
| **fetch-job**   | GCS ダウンロード        | GCS bucket/name   | ローカル mp3 パス  |
| **process-job** | Vertex AI 処理          | mp3 ファイル      | JSON メタデータ    |
| **upload-job**  | R2 アップロード         | メタデータ + mp3  | R2 URL + RSS       |
| **notify-job**  | 通知送信                | 状態 (成功/失敗)  | Discord メッセージ |

## 共有ライブラリの使用

`app/shared/` は各ジョブコンテナで COPY され、`sys.path` に追加されます。

例: `fetch-job` の Dockerfile：

```dockerfile
COPY ../shared /app/shared
ENV PYTHONPATH=/app/shared:$PYTHONPATH
```

## デプロイ

各ジョブは以下の手順で Container Registry にプッシュ・デプロイされます：

```bash
# 例: fetch-job をビルド
cd app/fetch-job
docker build -t gcr.io/<project>/fetch-job:latest .
docker push gcr.io/<project>/fetch-job:latest
```

Terraform では各 `google_cloud_run_v2_job` リソースで異なるイメージを指定します。
