"""Transfer an object from GCS to Cloudflare R2 via streaming.

Usage:
  PROJECT_ID=... ENDPOINT_URL=... R2_BUCKET=... \
  CLOUDFLARE_ACCESS_KEY_ID=... CLOUDFLARE_SECRET_ACCESS_KEY=... \
  python app/examples/example_storage_transfer_gcs2r2.py <gcs_bucket> <gcs_object_name> <r2_remote_key>

  uv run python examples/example_storage_transfer_gcs2r2.py podcast-automator-audio-input-dev short_dialogue.m4a test/ep/episode1.m4a
  """

import mimetypes
import os
import sys

import dotenv
from services import GCSClient, R2Client, transfer_gcs_to_r2

dotenv.load_dotenv()


def main():
    if len(sys.argv) < 4:
        print(
            "Usage: example_storage_transfer_gcs2r2.py "
            "<gcs_bucket> <gcs_object_name> <r2_remote_key>"
        )
        sys.exit(1)

    gcs_bucket_name = sys.argv[1]
    gcs_object_name = sys.argv[2]
    r2_remote_key = sys.argv[3]

    project_id = os.environ.get("PROJECT_ID", "sunabalog-dev")
    print("Project ID:", project_id)
    endpoint_url = os.environ.get(
        "ENDPOINT_URL",
        "https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com",
    )
    r2_bucket = os.environ.get("R2_BUCKET", "podcast")
    access_key = os.environ.get("CLOUDFLARE_ACCESS_KEY_ID")
    secret_key = os.environ.get("CLOUDFLARE_SECRET_ACCESS_KEY")
    custom_domain = os.environ.get("R2_CUSTOM_DOMAIN")

    if not all([project_id, endpoint_url, r2_bucket, access_key, secret_key]):
        raise SystemExit(
            "Set PROJECT_ID, ENDPOINT_URL, R2_BUCKET, "
            "CLOUDFLARE_ACCESS_KEY_ID, CLOUDFLARE_SECRET_ACCESS_KEY"
        )

    r2_client = R2Client(
        project_id=project_id,
        endpoint_url=endpoint_url,
        bucket_name=r2_bucket,
        access_key=access_key,
        secret_key=secret_key,
    )
    gcs_client = GCSClient(project_id=project_id)

    content_type = mimetypes.guess_type(gcs_object_name)[0] or "audio/mpeg"
    print("Content type:", content_type)
    # Fail fast if the source object is missing or not accessible
    blob = gcs_client.client.bucket(gcs_bucket_name).blob(gcs_object_name)
    if not blob.exists():
        raise SystemExit(
            f"GCS object not found or not accessible: gs://{gcs_bucket_name}/{gcs_object_name}"
        )


    url, size, duration = transfer_gcs_to_r2(
        gcs_client=gcs_client,
        r2_client=r2_client,
        gcs_bucket_name=gcs_bucket_name,
        gcs_object_name=gcs_object_name,
        r2_remote_key=r2_remote_key,
        content_type=content_type,
        public=True,
        custom_domain=custom_domain,
    )
    print("Uploaded to:", url, f"Size: {size} bytes", f"Duration: {duration} sec")


if __name__ == "__main__":
    main()