#!/usr/bin/env python3
"""
R2 からファイルをダウンロードする簡易スクリプト。

使い方:
  PROJECT_ID=... SECRET_NAME=... ENDPOINT_URL=... BUCKET_NAME=... \
  python app/podcast-processor/scripts/download_r2.py remote/key/path.mp3 --out local.mp3
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from services import R2Client


def main():
    parser = argparse.ArgumentParser(description="Download a file from Cloudflare R2 via R2Client")
    parser.add_argument("remote_key", help="R2 のオブジェクトキー（例: folder/file.mp3）")
    parser.add_argument("--out", "-o", help="保存先ローカルパス（省略時は同名で保存）")
    args = parser.parse_args()

    project_id = os.environ.get("PROJECT_ID", "taka-test-481815")
    secret_name = os.environ.get("SECRET_NAME", "sunabalog-r2")
    endpoint_url = os.environ.get(
        "ENDPOINT_URL", "https://8ed20f6872cea7c9219d68bfcf5f98ae.r2.cloudflarestorage.com"
    )
    bucket_name = os.environ.get("BUCKET_NAME", "podcast")

    if not all([project_id, secret_name, endpoint_url, bucket_name]):
        raise SystemExit(
            "環境変数 PROJECT_ID, SECRET_NAME, ENDPOINT_URL, BUCKET_NAME を設定してください。"
        )

    client = R2Client(
        project_id=project_id,
        secret_name=secret_name,
        endpoint_url=endpoint_url,
        bucket_name=bucket_name,
    )

    print(f"Downloading {args.remote_key} from bucket {bucket_name} ...")
    data = client.download_file(args.remote_key)

    out_path = args.out or os.path.basename(args.remote_key)
    with open(out_path, "wb") as f:
        f.write(data)

    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
