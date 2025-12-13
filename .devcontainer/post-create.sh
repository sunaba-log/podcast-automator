#!/bin/bash

set -e

echo "=== podcast-automator Dev Container Setup ==="

# Python 環境設定
echo "📦 Setting up Python environment..."

# 全ジョブの requirements を統合して依存関係をインストール
pip install --upgrade pip setuptools wheel

# Shared library
pip install -e app/shared/

# 各ジョブの依存関係
pip install -r app/controller/requirements.txt
pip install -r app/fetch-job/requirements.txt
pip install -r app/process-job/requirements.txt
pip install -r app/upload-job/requirements.txt
pip install -r app/notify-job/requirements.txt

# 開発用ツール
echo "🛠️ Installing development tools..."
pip install \
  pytest \
  pytest-cov \
  black \
  ruff \
  mypy \
  pylint \
  flake8 \
  pytest-mock \
  hypothesis

# Terraform & gcloud
echo "☁️ Verifying Terraform & gcloud..."
terraform version
gcloud version

# Git設定
echo "📝 Configuring Git..."
git config --global --add safe.directory /workspace

# 開発用エイリアス作成
echo "✨ Setting up development aliases..."
cat >> ~/.bashrc << 'EOF'

# podcast-automator aliases
alias pytest-app='cd /workspace && pytest app/ -v --cov=app/shared'
alias fmt-python='cd /workspace && ruff check app/ --fix && black app/'
alias test-fetch='cd /workspace && python -m pytest app/fetch-job/tests/ -v'
alias test-process='cd /workspace && python -m pytest app/process-job/tests/ -v'
alias test-upload='cd /workspace && python -m pytest app/upload-job/tests/ -v'
alias test-notify='cd /workspace && python -m pytest app/notify-job/tests/ -v'
alias tf-plan='cd /workspace/terraform && terraform plan -var-file=terraform.tfvars'
alias tf-apply='cd /workspace/terraform && terraform apply -var-file=terraform.tfvars'

EOF

echo "✅ Setup complete!"
echo ""
echo "🚀 Available commands:"
echo "  pytest-app       - Run all tests with coverage"
echo "  fmt-python       - Format Python code (ruff + black)"
echo "  test-<job>       - Run tests for specific job"
echo "  tf-plan          - Terraform plan"
echo "  tf-apply         - Terraform apply"
echo ""
echo "📚 Documentation:"
echo "  - JOB_ARCHITECTURE.md - Job architecture & design"
echo "  - DEPLOYMENT.md - GCP deployment guide"
echo "  - README.md - Project overview"
