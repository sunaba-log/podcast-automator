FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# COPY ../shared /app/shared
COPY services /app/services
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./

# ENV PYTHONPATH=/app/shared:$PYTHONPATH
ENTRYPOINT ["python", "main.py"]
