# Dev Container Setup Guide

このディレクトリは、podcast-automator の開発環境を VS Code Dev Container で構築するための設定ファイルを格納しています。

## 📋 概要

Dev Container を使用することで、以下が得られます：

- **一貫性**: すべての開発者が同じ環境で作業
- **再現性**: 環境の差異による問題を排除
- **クリーン性**: ホストマシンにインストールせずに開発可能

## 🚀 セットアップ手順

### 1. 前提条件

- **VS Code** をインストール
- **Docker** をインストール（Docker Desktop が推奨）
- **Remote - Containers** 拡張機能をインストール
  ```
  ext install ms-vscode-remote.remote-containers
  ```

### 2. Dev Container を起動

#### 方法 A: VS Code コマンドパレット

1. VS Code を開く
2. `Ctrl+Shift+P` (macOS: `Cmd+Shift+P`) でコマンドパレットを開く
3. "Dev Containers: Reopen in Container" を検索・実行

#### 方法 B: VS Code UI

1. VS Code 画面左下の "Open in Remote Window" アイコンをクリック
2. "Reopen in Container" を選択

### 3. セットアップの確認

自動セットアップが完了すると、以下が行われています：

- Python 3.11 がインストール
- Docker、Terraform、gcloud CLI が利用可能
- 全ジョブの依存関係がインストール
- 開発用ツール（pytest、ruff、black など）がインストール
- 開発用エイリアスが登録

## 🛠️ 開発用コマンド

### Python テスト

```bash
# 全ジョブのテスト実行（カバレッジ付き）
pytest-app

# 特定ジョブのテスト実行
test-fetch
test-process
test-upload
test-notify
```

### コード フォーマット & リント

```bash
# Ruff + Black でコードフォーマット
fmt-python

# 個別フォーマット
ruff check app/ --fix        # Ruff でリント修正
black app/                   # Black でコードフォーマット
mypy app/                    # Type check
```

### Terraform

```bash
# デプロイ計画の確認
tf-plan

# デプロイ実行
tf-apply
```

### GCP 認証

```bash
# Google Cloud 認証
gcloud auth login

# プロジェクト設定
gcloud config set project <your-project-id>
```

### Docker

```bash
# 各ジョブをビルド
cd app/fetch-job && docker build -t fetch-job:latest .
cd ../process-job && docker build -t process-job:latest .
```

## 📁 ファイル構成

```
.devcontainer/
├── devcontainer.json          # Dev Container 設定
├── Dockerfile                 # 自動セットアップ用 Dockerfile（オプション）
├── post-create.sh             # セットアップ後の実行スクリプト
└── README.md                  # このファイル
```

### devcontainer.json

- **image**: Python 3.11 公式イメージ（Microsoft 提供）
- **features**: Docker、Terraform、gcloud CLI を追加
- **extensions**: VS Code 拡張機能（Python、Terraform、Docker 等）
- **forwardPorts**: ポート 8080、8888 をフォワード
- **postCreateCommand**: セットアップスクリプトを自動実行

### post-create.sh

セットアップ後に自動実行される処理：

1. Python 依存関係のインストール
2. 共有ライブラリ (`app/shared/`) のインストール
3. 各ジョブの `requirements.txt` をインストール
4. 開発用ツール（pytest、ruff 等）をインストール
5. Git 設定
6. 開発用エイリアス設定

## 💡 使用例

### シナリオ 1: fetch-job の開発・テスト

```bash
# Dev Container に入っている状態で：

# 1. fetch-job のソースコード修正
code app/fetch-job/main.py

# 2. テスト実行
pytest app/fetch-job/tests/ -v

# 3. コードフォーマット
fmt-python

# 4. ローカルビルド・テスト
cd app/fetch-job
docker build -t fetch-job:dev .
docker run --rm fetch-job:dev \
  --job-id test-123 \
  --bucket podcast-input-dev \
  --object-name test.mp3
```

### シナリオ 2: Terraform デプロイ計画

```bash
# 1. GCP 認証
gcloud auth login
gcloud config set project your-gcp-project

# 2. Terraform 変数ファイル設定
cd terraform
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集

# 3. デプロイ計画確認
tf-plan

# 4. デプロイ実行
tf-apply
```

### シナリオ 3: ポートフォワード（ローカルテスト）

Controller (Cloud Run Service) のローカルテスト：

```bash
# Dev Container 内：
cd app/controller
python main.py

# ホストマシンのブラウザ or ターミナルから：
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{"bucket":"test","name":"test.mp3"}'
```

## 🔍 トラブルシューティング

### Dev Container が起動しない

```bash
# キャッシュをクリアして再試行
# VS Code コマンドパレット: "Dev Containers: Rebuild Container"
```

### Docker デーモンに接続できない

```bash
# Docker Desktop が実行中か確認
# Docker Desktop を起動してから再度試行
```

### ポートが既に使用されている

```bash
# devcontainer.json の forwardPorts を変更
# または ホストマシンで該当ポートを解放
```

### pip インストール失敗

```bash
# コンテナをリビルド
# VS Code コマンドパレット: "Dev Containers: Rebuild Container"

# または手動でインストール
pip install --upgrade pip
pip install -r app/<job>/requirements.txt
```

## 📚 参考資料

- [VS Code Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Dev Containers Specification](https://containers.dev/)
- [Microsoft Python Dev Container Image](https://github.com/microsoft/vscode-dev-containers/tree/main/containers/python)

## ✅ 環境確認

Dev Container 起動後、以下で環境を確認できます：

```bash
# Python バージョン
python --version

# 依存パッケージ確認
pip list

# Docker
docker version

# Terraform
terraform version

# gcloud
gcloud version
```

## 🎯 次のステップ

1. **各ジョブの開発**

   - `app/fetch-job/main.py` など、各ジョブを開発・テスト

2. **ユニットテスト追加**

   - `app/<job>/tests/` ディレクトリを作成し、テストを追加

3. **統合テスト**

   - ローカルで複数ジョブを連携してテスト

4. **GCP へのデプロイ**
   - Terraform を使用して本番環境へデプロイ
