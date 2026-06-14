"""Cloudflare R2 and GCS infrastructure clients."""

import io
import json
import logging

import boto3
from botocore.exceptions import ClientError
from google.cloud import secretmanager_v1, storage
from pydub import AudioSegment

from domain.interfaces import BlobSource, ObjectStorage

logger = logging.getLogger(__name__)


class R2Client(ObjectStorage):
    """Cloudflare R2 client."""

    def __init__(
        self,
        project_id: str,
        endpoint_url: str,
        bucket_name: str,
        secret_name: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize R2 client with bucket settings and credentials source."""
        self.project_id = project_id
        self.endpoint_url = endpoint_url
        self.bucket_name = bucket_name

        if access_key and secret_key:
            self.access_key = access_key
            self.secret_key = secret_key
        else:
            self.access_key, self.secret_key = self._get_credentials(secret_name)

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="auto",
        )

    def _get_credentials(self, secret_name: str | None) -> tuple[str, str]:
        """Get R2 credentials from Secret Manager."""
        if secret_name is None:
            raise ValueError("secret_name is required to get R2 credentials from Secret Manager.")

        try:
            client = secretmanager_v1.SecretManagerServiceClient()
            secret_path = client.secret_version_path(self.project_id, secret_name, "latest")
            response = client.access_secret_version(request={"name": secret_path})

            secret_data = json.loads(response.payload.data.decode("UTF-8"))
            return secret_data["r2_access_key"], secret_data["r2_secret_key"]
        except Exception:
            logger.exception("Failed to get R2 credentials")
            raise

    def download_file(self, remote_key: str) -> bytes:
        """Download a file from R2."""
        try:
            file_bytes = self.client.get_object(Bucket=self.bucket_name, Key=remote_key)["Body"].read()
            logger.info("Downloaded %s from R2", remote_key)
        except ClientError:
            logger.exception("Failed to download file from R2:")
            raise
        return file_bytes

    def upload_file(
        self,
        file_content: bytes,
        remote_key: str,
        content_type: str | None = None,
        *,
        public: bool = False,
    ) -> str:
        """Upload file bytes to R2."""
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            if public:
                extra_args["ACL"] = "public-read"

            self.client.upload_fileobj(io.BytesIO(file_content), self.bucket_name, remote_key, ExtraArgs=extra_args)

            url = f"{self.endpoint_url}/{self.bucket_name}/{remote_key}"
            logger.info("Uploaded %s to R2: %s", remote_key, url)
            return url
        except ClientError:
            logger.exception("Failed to upload file to R2:")
            raise

    def generate_public_url(self, remote_key: str, custom_domain: str | None = None) -> str:
        """Generate a public URL for an R2 object."""
        if custom_domain:
            return f"https://{custom_domain}/{remote_key}"
        return f"{self.endpoint_url}/{self.bucket_name}/{remote_key}"


class GCSClient(BlobSource):
    """Google Cloud Storage client."""

    def __init__(self, project_id: str) -> None:
        """Initialize GCS client bound to the specified project."""
        self.client = storage.Client(project=project_id)

    def download_blob(self, bucket_name: str, object_name: str, destination_file_path: str) -> None:
        """Download blob to local file."""
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.download_to_filename(destination_file_path)
            logger.info("Downloaded gs://%s/%s to %s", bucket_name, object_name, destination_file_path)
        except Exception:
            logger.exception("Failed to download blob:")
            raise

    def download_blob_as_bytes(self, bucket_name: str, object_name: str) -> bytes:
        """Download blob as bytes."""
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            file_bytes = blob.download_as_bytes()
            logger.info("Downloaded gs://%s/%s as bytes", bucket_name, object_name)
            return file_bytes
        except Exception:
            logger.exception("Failed to download blob as bytes:")
            raise

    def upload_blob(
        self,
        bucket_name: str,
        source_file_path: str,
        destination_object_name: str,
        content_type: str | None = None,
    ) -> None:
        """Upload local file to GCS."""
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(destination_object_name)
            blob.upload_from_filename(source_file_path, content_type=content_type)
            logger.info("Uploaded %s to gs://%s/%s", source_file_path, bucket_name, destination_object_name)
        except Exception:
            logger.exception("Failed to upload blob:")
            raise

    def get_blob_metadata(self, bucket_name: str, object_name: str) -> dict:
        """Get blob metadata."""
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
        except Exception:
            logger.exception("Failed to get blob metadata:")
            raise

    def list_blobs(self, bucket_name: str, prefix: str | None = None) -> list:
        """List blobs in a bucket."""
        try:
            bucket = self.client.bucket(bucket_name)
            return list(bucket.list_blobs(prefix=prefix))
        except Exception:
            logger.exception("Failed to list blobs:")
            raise


def get_audio_info(file_buffer: io.BytesIO, audio_format: str) -> list:
    """Get audio file size and duration information."""
    file_size_bytes = file_buffer.getbuffer().nbytes
    logger.info("File size: %d bytes", file_size_bytes)

    sounds = AudioSegment.from_file(file=file_buffer, format=audio_format)
    logger.info("channel: %s", sounds.channels)
    logger.info("frame rate: %s", sounds.frame_rate)
    logger.info("duration: %s s", sounds.duration_seconds)

    duration_seconds = int(sounds.duration_seconds)
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60
    duration_str = f"{hours:02}:{minutes:02}:{seconds:02}"
    logger.info("Formatted duration: %s", duration_str)

    return [file_size_bytes, duration_str]
