from __future__ import annotations

import boto3

from src.config import get_settings


class R2Client:
    def __init__(self) -> None:
        settings = get_settings()
        self._bucket_name = settings.r2_bucket_name
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url or None,
            aws_access_key_id=settings.r2_access_key or None,
            aws_secret_access_key=settings.r2_secret_key or None,
        )

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> None:
        if not self._bucket_name:
            return
        self._client.put_object(
            Bucket=self._bucket_name, Key=key, Body=data, ContentType=content_type
        )
