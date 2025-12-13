"""Cloud Run Job: GCS から mp3 ファイルをダウンロード."""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add shared library to path
sys.path.insert(0, "/app/shared")

from shared.storage import GCSClient
from shared.logger import logger

logger.info("Starting fetch-job")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True, help="Job ID")
    parser.add_argument("--bucket", required=True, help="GCS bucket name")
    parser.add_argument("--object-name", required=True, help="GCS object name (mp3 file)")
    parser.add_argument("--output-path", default="/tmp/audio.mp3", help="Output file path")

    args = parser.parse_args()

    project_id = os.getenv("GCP_PROJECT_ID", "your-project")
    gcs = GCSClient(project_id)

    try:
        logger.info(f"Downloading {args.bucket}/{args.object_name} to {args.output_path}")

        # GCS からダウンロード
        gcs.download_blob(args.bucket, args.object_name, args.output_path)

        # ファイルサイズ確認
        file_size = Path(args.output_path).stat().st_size
        logger.info(f"Downloaded file size: {file_size} bytes")

        # 出力ファイル情報を JSON で stdout に出力（次のジョブで使用）
        import json

        output = {
            "status": "success",
            "job_id": args.job_id,
            "local_file": args.output_path,
            "file_size": file_size,
            "source_bucket": args.bucket,
            "source_object": args.object_name,
        }
        print(json.dumps(output))

    except Exception as e:
        logger.exception(f"Error in fetch-job: {e}")
        import json

        print(json.dumps({"status": "failed", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
