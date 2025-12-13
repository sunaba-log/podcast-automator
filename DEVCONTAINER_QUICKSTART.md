# Dev Container クイックスタート

podcast-automator を Dev Container で開発するための最短手順です。

## 🚀 30 秒で始める

### 1. VS Code で開く

```bash
code /Users/onotakayoshi/Documents/Projects/sunabalog/podcast-automator
```

### 2. Dev Container を起動

- VS Code 左下の "Open in Remote Window" アイコンをクリック
- または `Ctrl+Shift+P` → "Dev Containers: Reopen in Container"

### 3. 自動セットアップを待つ

自動でセットアップが完了します（初回は 3-5 分程度）。

## 🎯 よく使うコマンド

```bash
# テスト実行
make test                # 全テスト
make test-fetch          # fetch-job のテスト
make test-process        # process-job のテスト

# コード品質
make lint                # リント実行
make format              # コードフォーマット

# Docker イメージ
make build               # イメージビルド
make build-push          # ビルド + Registry へプッシュ

# Terraform
make tf-plan             # デプロイ計画
make tf-apply            # デプロイ実行
```

または短いエイリアス（post-create.sh で設定）：

```bash
pytest-app               # 全テスト
fmt-python               # フォーマット
tf-plan                  # Terraform計画
tf-apply                 # Terraform実行
```

## 📝 開発フロー例

### fetch-job を開発・テストする場合

```bash
# 1. ファイルを編集
code app/fetch-job/main.py

# 2. テスト実行
make test-fetch

# 3. コードフォーマット
make format

# 4. ローカルでビルド
cd app/fetch-job
docker build -t fetch-job:dev .

# 5. テスト実行
docker run --rm fetch-job:dev \
  --job-id test-123 \
  --bucket podcast-input \
  --object-name test.mp3
```

### GCP へデプロイする場合

```bash
# 1. GCP 認証
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. イメージビルド＆プッシュ
make build-push

# 3. デプロイ計画確認
make tf-plan

# 4. デプロイ実行
make tf-apply
```

## 📚 詳細ドキュメント

- **[.devcontainer/README.md](./.devcontainer/README.md)** - Dev Container の詳細設定
- **[JOB_ARCHITECTURE.md](./JOB_ARCHITECTURE.md)** - ジョブアーキテクチャ
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - GCP デプロイ手順
- **[README.md](./README.md)** - プロジェクト概要

## 🔧 トラブルシューティング

### "Dev Container が起動しない"

```bash
# コンテナをリビルド
# VS Code コマンドパレット → "Dev Containers: Rebuild Container"
```

### "Python パッケージが見つからない"

```bash
# 依存関係を再インストール
pip install -e app/shared/
pip install -r app/*/requirements.txt
pip install -r pyproject.toml[dev]
```

### "Docker イメージをビルドできない"

```bash
# Docker Desktop が起動しているか確認
docker ps
```

## ✅ セットアップ確認

```bash
# 以下を実行して環境を確認
python --version          # Python 3.11
docker version            # Docker CLI
terraform version         # Terraform
gcloud version            # Google Cloud CLI
pytest --version          # pytest
make test                 # 全テスト実行
```

全て正常に実行できれば、セットアップ完了です！🎉

## 🎓 次のステップ

1. [JOB_ARCHITECTURE.md](./JOB_ARCHITECTURE.md) を読む
2. 各ジョブの実装を確認
3. `make test` でテストを実行
4. 必要に応じてコードを修正
5. GCP へデプロイ

Happy coding! 🚀
