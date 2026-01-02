#!/usr/bin/env python3
"""List objects in a GCS bucket.

Usage:
  PROJECT_ID=... python app/examples/example_list_gcs_objects.py <gcs_bucket>
"""

import os
import sys

import dotenv
from services import GCSClient

dotenv.load_dotenv()


def main():
    if len(sys.argv) < 2:
        print("Usage: example_list_gcs_objects.py <gcs_bucket>")
        sys.exit(1)

    gcs_bucket_name = sys.argv[1]
    project_id = os.environ.get("PROJECT_ID", "sunabalog-dev")

    print(f"Project ID: {project_id}")
    print(f"Bucket: {gcs_bucket_name}")
    print("-" * 60)

    gcs_client = GCSClient(project_id=project_id)
    blobs = gcs_client.list_blobs(bucket_name=gcs_bucket_name, prefix=None)

    objects = list(blobs)
    if not objects:
        print("No objects found in bucket.")
        return

    print(f"Found {len(objects)} object(s):\n")
    for blob in objects:
        print(f"  Name: {blob.name}")
        print(f"  Size: {blob.size} bytes")
        print(f"  Updated: {blob.updated}")
        print()


if __name__ == "__main__":
    main()
