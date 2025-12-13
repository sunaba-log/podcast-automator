"""GCS操作ライブラリ."""

from google.cloud import storage
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GCSClient:
    def __init__(self, project_id: str):
        self.client = storage.Client(project=project_id)

    def download_blob(
        self, bucket_name: str, object_name: str, destination_file_path: str
    ) -> None:
        """GCS から blob をダウンロード."""
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.download_to_filename(destination_file_path)
            logger.info(
                f"Downloaded gs://{bucket_name}/{object_name} to {destination_file_path}"
            )
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
