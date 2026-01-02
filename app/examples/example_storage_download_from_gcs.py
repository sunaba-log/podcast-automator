#!/usr/bin/env python3
"""
R2 からファイルをダウンロードする簡易スクリプト。

使い方:
  PROJECT_ID=... SECRET_NAME=... ENDPOINT_URL=... BUCKET_NAME=... \
  python app/examples/example_storage_download_from_gcs.py 20251231_sunabalog_recording.m4a --out 20251231_sunabalog_recording.m4a
"""

import argparse
import os

from services import GCSClient


def main():
    parser = argparse.ArgumentParser(description="Download a file from Cloudflare R2 via R2Client")
    parser.add_argument("remote_key", help="R2 のオブジェクトキー(例: folder/file.mp3)")
    parser.add_argument("--out", "-o", help="保存先ローカルパス(省略時は同名で保存)")
    args = parser.parse_args()

    project_id = os.environ.get("PROJECT_ID", "sunabalog-dev")
    bucket_name = os.environ.get("BUCKET_NAME", "podcast-automator-audio-input-dev")

    if not all([project_id, bucket_name]):
        raise SystemExit("環境変数 PROJECT_ID, BUCKET_NAME を設定してください。")

    client = GCSClient(
        project_id=project_id,
    )

    print(f"Downloading {args.remote_key} from bucket {bucket_name} ...")
    out_path = args.out or os.path.basename(args.remote_key)
    client.download_blob(bucket_name=bucket_name, object_name=args.remote_key, destination_file_path=out_path)

    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
