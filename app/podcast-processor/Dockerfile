FROM python:3.12-slim

# 1. uvのバイナリを取得（公式イメージからコピーするのがベストプラクティス）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 2. OS依存パッケージ (ffmpeg) のインストール
# --no-install-recommends をつけて不要な推奨パッケージを除外
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 3. 依存定義ファイルのみ先にコピー（★重要）
# ソースコード(services/main.py)が変わっても、ここが変わらなければ
# 次の uv sync はキャッシュされ、爆速で終わります。
COPY pyproject.toml uv.lock ./

# 4. 依存関係のインストール
# uv sync はデフォルトで .venv を作成します。
# --frozen: lockファイルとtomlの整合性をチェック
# --no-dev: 本番環境なら開発用依存（pytestなど）を除外する場合に追加
RUN uv sync --frozen --no-cache

# 5. PATHの設定（★重要）
# uv sync で作られた仮想環境(.venv)のパスを優先パスに追加します。
# これにより "python" コマンドが .venv/bin/python を指すようになります。
ENV PATH="/app/.venv/bin:$PATH"

# 6. ソースコードのコピー
# ここを最後に持ってくることで、コード修正時の再ビルドを高速化
COPY services /app/services
COPY main.py ./

# ENV PYTHONPATH=/app/shared:$PYTHONPATH
ENTRYPOINT ["python", "main.py"]