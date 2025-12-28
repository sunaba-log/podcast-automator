#!/usr/bin/env python3
"""
Upload a local audio file to R2 using R2Client.upload_file
Usage:
  PROJECT_ID=... SECRET_NAME=... ENDPOINT_URL=... BUCKET_NAME=... \
  python upload_audio.py local/path/to/file.mp3 remote/key/in/bucket.mp3
  python example_storage_transfer_gcs2r2.py ./data/short_dialogue.m4a test/ep/episode1.m4a
"""

import mimetypes
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import GCSClient, R2Client, transfer_gcs_to_r2


def main():
    if len(sys.argv) < 3:
        print("Usage: upload_audio.py <local_path> <remote_key>")
        sys.exit(1)

    local_path = sys.argv[1]
    remote_key = sys.argv[2]

    project_id = os.environ.get("PROJECT_ID", "taka-test-481815")
    secret_name = os.environ.get("SECRET_NAME", "podcast-automator")
    endpoint_url = os.environ.get(
        "ENDPOINT_URL", "https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com"
    )
    bucket_name = os.environ.get("BUCKET_NAME", "podcast")

    if not all([project_id, secret_name, endpoint_url, bucket_name]):
        raise SystemExit("Set PROJECT_ID, SECRET_NAME, ENDPOINT_URL, BUCKET_NAME env vars")

    r2_client = R2Client(
        project_id=project_id,
        secret_name=secret_name,
        endpoint_url=endpoint_url,
        bucket_name=bucket_name,
    )
    gcs_client = GCSClient(project_id=project_id)

    content_type = mimetypes.guess_type(local_path)[0] or "audio/mpeg"
    url, size, duration = transfer_gcs_to_r2(
        gcs_client=gcs_client,
        r2_client=r2_client,
        gcs_bucket_name="sample-audio-for-sunabalog",
        gcs_object_name="short_dialogue.m4a",
        r2_remote_key=remote_key,
        content_type=content_type,
        public=True,
    )
    print("Uploaded to:", url, f"Size: {size} bytes", f"Duration: {duration} sec")


if __name__ == "__main__":
    main()
