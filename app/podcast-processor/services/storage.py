"""Cloudflare R2 操作ライブラリ."""

import io
import json
import logging
import os
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from google.cloud import secretmanager_v1, storage
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class R2Client:
    """Cloudflare R2 操作用のクライアント.
    functions:
        - download_file(remote_key: str) -> bytes
        - upload_file(file_content: bytes, remote_key: str, content_type: Optional[str] = None, public: bool = False) -> str
        - upload_json(data: dict, remote_key: str, public: bool = True) -> str
        - generate_public_url(remote_key: str, custom_domain: Optional[str] = None) -> str
    """

    def __init__(
        self,
        project_id: str,
        endpoint_url: str,
        bucket_name: str,
        secret_name: str = "",
        access_key: str = None,
        secret_key: str = None,
    ):
        self.project_id = project_id
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name

        # Secret Manager から認証情報を取得
        if access_key and secret_key:
            self.access_key = access_key
            self.secret_key = secret_key
        else:
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
            client = secretmanager_v1.SecretManagerServiceClient()
            secret_path = client.secret_version_path(self.project_id, secret_name, "latest")
            response = client.access_secret_version(request={"name": secret_path})

            secret_data = json.loads(response.payload.data.decode("UTF-8"))
            return secret_data["r2_access_key"], secret_data["r2_secret_key"]
        except Exception as e:
            logger.error(f"Failed to get R2 credentials: {e}")
            raise

    def download_file(self, remote_key: str) -> bytes:
        """R2 からファイルをダウンロード."""
        try:
            file_bytes = self.client.get_object(Bucket=self.bucket_name, Key=remote_key)[
                "Body"
            ].read()
            logger.info(f"Downloaded {remote_key} from R2")
        except ClientError as e:
            logger.error(f"Failed to download file from R2: {e}")
            raise
        return file_bytes

    def upload_file(
        self,
        file_content: bytes,
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

            self.client.upload_fileobj(
                io.BytesIO(file_content), self.bucket_name, remote_key, ExtraArgs=extra_args
            )

            url = f"{self.endpoint_url}/{self.bucket_name}/{remote_key}"
            logger.info(f"Uploaded {remote_key} to R2: {url}")
            return url
        except ClientError as e:
            logger.error(f"Failed to upload file to R2: {e}")
            raise

    def upload_json(self, data: dict, remote_key: str, public: bool = True) -> str:
        """JSON データを R2 にアップロード."""
        import json
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(data, f)
                temp_path = f.name

            return self.upload_file(
                temp_path, remote_key, content_type="application/json", public=public
            )
        finally:
            import os

            if os.path.exists(temp_path):
                os.remove(temp_path)

    def generate_public_url(self, remote_key: str, custom_domain: Optional[str] = None) -> str:
        """R2 ファイルの公開 URL を生成."""
        if custom_domain:
            return f"https://{custom_domain}/{remote_key}"
        return f"{self.endpoint_url}/{self.bucket_name}/{remote_key}"


class GCSClient:
    """GCS 操作用のクライアント.

    Methods:
        - download_blob(bucket_name: str, object_name: str, destination_file_path: str) -> None
        - upload_blob(bucket_name: str, source_file_path: str, destination_object_name: str, content_type: Optional[str] = None) -> None
        - get_blob_metadata(bucket_name: str, object_name: str) -> dict
        - list_blobs(bucket_name: str, prefix: Optional[str] = None) -> list
    """

    def __init__(self, project_id: str):
        """GCS 操作用のクライアント.
        Args:
            project_id: GCP プロジェクトID.
        """
        self.client = storage.Client(project=project_id)

    def download_blob(self, bucket_name: str, object_name: str, destination_file_path: str) -> None:
        """GCS から blob をダウンロード.
        Docs: https://docs.cloud.google.com/storage/docs/downloading-objects?hl=ja
        Args:
            bucket_name: GCS バケット名.
            object_name: ダウンロードするオブジェクト名.
            destination_file_path: ダウンロード先のローカルファイルパス.
        Returns:
            None
        Raises:
            Exception: ダウンロードに失敗した場合.
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.download_to_filename(destination_file_path)
            logger.info(f"Downloaded gs://{bucket_name}/{object_name} to {destination_file_path}")
        except Exception as e:
            logger.error(f"Failed to download blob: {e}")
            raise

    def upload_blob(
        self,
        bucket_name: str,
        source_file_path: str,
        destination_object_name: str,
        content_type: Optional[str] = None,
    ) -> None:
        """ファイルを GCS にアップロード."""
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(destination_object_name)
            blob.upload_from_filename(source_file_path, content_type=content_type)
            logger.info(
                f"Uploaded {source_file_path} to gs://{bucket_name}/{destination_object_name}"
            )
        except Exception as e:
            logger.error(f"Failed to upload blob: {e}")
            raise

    def get_blob_metadata(self, bucket_name: str, object_name: str) -> dict:
        """Blob のメタデータを取得."""
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.reload()
            return {
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "updated": blob.updated,
            }
        except Exception as e:
            logger.error(f"Failed to get blob metadata: {e}")
            raise

    def list_blobs(self, bucket_name: str, prefix: Optional[str] = None) -> list:
        """バケット内の blob をリスト."""
        try:
            bucket = self.client.bucket(bucket_name)
            return list(bucket.list_blobs(prefix=prefix))
        except Exception as e:
            logger.error(f"Failed to list blobs: {e}")
            raise


def transfer_gcs_to_r2(
    gcs_client: GCSClient,
    r2_client: R2Client,
    gcs_bucket_name: str,
    gcs_object_name: str,
    r2_remote_key: str,
    content_type: Optional[str] = None,
    public: bool = True,
    custom_domain: Optional[str] = None,
) -> List[str]:
    """GCS から R2 へファイルを転送.

    Args:
        gcs_client: GCS クライアント.
        r2_client: R2 クライアント.
        gcs_bucket_name: GCS バケット名.
        gcs_object_name: GCS オブジェクト名.
        r2_remote_key: R2 リモートキー.
        content_type: コンテンツタイプ.
        public: 公開するかどうか.
        custom_domain: カスタムドメイン.

    Returns:
        R2 にアップロードされたファイルの公開 URL.
    """
    fn, ext = os.path.splitext(gcs_object_name)
    format = ext.lstrip(".").lower()

    try:
        # GCS からファイルをダウンロード
        with io.BytesIO() as file_buffer:
            bucket = gcs_client.client.bucket(gcs_bucket_name)
            blob = bucket.blob(gcs_object_name)
            blob.download_to_file(file_buffer)
            file_buffer.seek(0)

            # オーディオ情報を取得
            try:
                file_size_bytes, duration_str = get_audio_info(
                    file_buffer=file_buffer, format=format
                )
            except Exception as e:
                logger.warning(f"Failed to get audio info: {e}")
                file_size_bytes, duration_str = -1, "00:00:00"

            # R2 にファイルをアップロード
            r2_url = r2_client.upload_file(
                file_content=file_buffer.read(),
                remote_key=r2_remote_key,
                content_type=content_type,
                public=public,
            )
        logger.info(f"Transferred gs://{gcs_bucket_name}/{gcs_object_name} to R2: {r2_url}")
        public_url = r2_client.generate_public_url(
            remote_key=r2_remote_key, custom_domain=custom_domain
        )
        return public_url, file_size_bytes, duration_str
    except Exception as e:
        logger.error(f"Failed to transfer file from GCS to R2: {e}")
        raise


def get_audio_info(file_buffer: io.BytesIO, format: str) -> list:
    # ファイルのサイズ（バイト数）を取得
    file_size_bytes = file_buffer.getbuffer().nbytes
    print(f"File size: {file_size_bytes} bytes")

    # ボイスメモで収録したm4aファイルを読み込む
    sounds = AudioSegment.from_file(file=file_buffer, format=format)
    # 基本情報の表示
    print(f"channel: {sounds.channels}")
    print(f"frame rate: {sounds.frame_rate}")
    print(f"duration: {sounds.duration_seconds} s")

    # 再生時間（例: "01:23:45"）
    duration_seconds = int(sounds.duration_seconds)
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60
    duration_str = f"{hours:02}:{minutes:02}:{seconds:02}"
    print(f"Formatted duration: {duration_str}")

    return [file_size_bytes, duration_str]
