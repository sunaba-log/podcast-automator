FROM python:3.11-slim

WORKDIR /app

# 共有ライブラリをコピー
COPY ../shared /app/shared
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

ENV PYTHONPATH=/app/shared:$PYTHONPATH
ENTRYPOINT ["python", "main.py"]
