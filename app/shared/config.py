"""Shared configuration & environment variables."""

import os
from typing import Optional


class Config:
    """環境変数から設定を読み込む."""

    # GCP
    PROJECT_ID = os.getenv("GCP_PROJECT_ID", "your-project")
    REGION = os.getenv("GCP_REGION", "asia-northeast1")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

    # GCS
    INPUT_BUCKET = os.getenv("GCS_INPUT_BUCKET", "podcast-input")
    OUTPUT_BUCKET = os.getenv("GCS_OUTPUT_BUCKET", "podcast-output")

    # Cloudflare R2
    R2_ENDPOINT = os.getenv(
        "R2_ENDPOINT_URL", "https://<account>.r2.cloudflarestorage.com"
    )
    R2_BUCKET = os.getenv("R2_BUCKET", "podcast-media")
    R2_CUSTOM_DOMAIN = os.getenv("R2_CUSTOM_DOMAIN", "https://media.example.com")

    # Vertex AI
    VERTEX_AI_MODEL = os.getenv("VERTEX_AI_MODEL", "gemini-1.5-pro")
    VERTEX_AI_LOCATION = os.getenv("VERTEX_AI_LOCATION", "asia-northeast1")

    # Secret Manager
    R2_KEYS_SECRET_NAME = os.getenv("R2_KEYS_SECRET_NAME", "cloudflare-r2-keys")
    DISCORD_WEBHOOK_SECRET_NAME = os.getenv(
        "DISCORD_WEBHOOK_SECRET_NAME", "discord-webhook-url"
    )

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Job control
    JOB_TIMEOUT = int(os.getenv("JOB_TIMEOUT", "600"))  # 10 min
    JOB_MAX_RETRIES = int(os.getenv("JOB_MAX_RETRIES", "2"))

    @classmethod
    def validate(cls):
        """必須設定を検証."""
        required = [cls.PROJECT_ID, cls.INPUT_BUCKET, cls.OUTPUT_BUCKET]
        for req in required:
            if not req or req == "your-project":
                raise ValueError(f"Missing required config: {req}")
