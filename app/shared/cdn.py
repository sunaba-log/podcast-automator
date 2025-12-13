"""Cloudflare R2 操作ライブラリ."""

import boto3
import logging
from botocore.exceptions import BotoCoreError, ClientError
from typing import Optional
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class R2Client:
    def __init__(
        self, project_id: str, secret_name: str, endpoint_url: str, bucket_name: str
    ):
        self.project_id = project_id
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name

        # Secret Manager から認証情報を取得
        self.access_key, self.secret_key = self._get_credentials(secret_name)

        # S3 クライアントを初期化（R2は S3 互換API）
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="auto",
        )

    def _get_credentials(self, secret_name: str) -> tuple:
        """Secret Manager から R2 認証情報を取得."""
        try:
            client = secretmanager.SecretManagerServiceClient()
            secret_path = client.secret_version_path(
                self.project_id, secret_name, "latest"
            )
            response = client.access_secret_version(request={"name": secret_path})

            import json

            secret_data = json.loads(response.payload.data.decode("UTF-8"))
            return secret_data["access_key_id"], secret_data["secret_access_key"]
        except Exception as e:
            logger.error(f"Failed to get R2 credentials: {e}")
            raise

    def upload_file(
        self,
        local_file_path: str,
        remote_key: str,
        content_type: Optional[str] = None,
        public: bool = False,
    ) -> str:
        """ファイルを R2 にアップロード."""
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            if public:
                extra_args["ACL"] = "public-read"

            self.client.upload_file(
                local_file_path,
                self.bucket_name,
                remote_key,
                ExtraArgs=extra_args,
            )

            url = f"{self.endpoint_url}/{self.bucket_name}/{remote_key}"
            logger.info(f"Uploaded {local_file_path} to R2: {url}")
            return url
        except ClientError as e:
            logger.error(f"Failed to upload file to R2: {e}")
            raise

    def upload_json(self, data: dict, remote_key: str, public: bool = True) -> str:
        """JSON データを R2 にアップロード."""
        import json
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump(data, f)
                temp_path = f.name

            return self.upload_file(
                temp_path, remote_key, content_type="application/json", public=public
            )
        finally:
            import os

            if os.path.exists(temp_path):
                os.remove(temp_path)

    def generate_public_url(
        self, remote_key: str, custom_domain: Optional[str] = None
    ) -> str:
        """R2 ファイルの公開 URL を生成."""
        if custom_domain:
            return f"{custom_domain}/{remote_key}"
        return f"{self.endpoint_url}/{self.bucket_name}/{remote_key}"
