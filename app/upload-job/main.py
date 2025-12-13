"""Cloud Run Job: メタデータ + 音声を Cloudflare R2 にアップロード."""

import sys
import os
import argparse
import json
import logging

# Add shared library to path
sys.path.insert(0, "/app/shared")

from shared.cdn import R2Client
from shared.storage import GCSClient
from shared.logger import logger

logger.info("Starting upload-job")


def generate_rss(metadata: dict, audio_url: str) -> str:
    """簡単な RSS フィードを生成 (テンプレート)."""
    rss_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Podcast</title>
    <link>https://example.com</link>
    <description>Auto-generated podcast feed</description>
    <item>
      <title>{metadata.get("title", "Untitled")}</title>
      <description>{metadata.get("summary", "No summary")}</description>
      <link>{audio_url}</link>
      <enclosure url="{audio_url}" type="audio/mpeg" />
      <pubDate>2025-12-13T00:00:00Z</pubDate>
    </item>
  </channel>
</rss>"""
    return rss_template


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True, help="Job ID")
    parser.add_argument("--audio-file", required=True, help="Local audio file path")
    parser.add_argument("--metadata-json", required=True, help="JSON metadata")

    args = parser.parse_args()

    project_id = os.getenv("GCP_PROJECT_ID", "your-project")
    r2_endpoint = os.getenv(
        "R2_ENDPOINT_URL", "https://<account>.r2.cloudflarestorage.com"
    )
    r2_bucket = os.getenv("R2_BUCKET", "podcast-media")
    r2_custom_domain = os.getenv("R2_CUSTOM_DOMAIN", "")
    r2_keys_secret = os.getenv("R2_KEYS_SECRET_NAME", "cloudflare-r2-keys")

    try:
        logger.info(f"Uploading to R2: {r2_bucket}")

        r2_client = R2Client(project_id, r2_keys_secret, r2_endpoint, r2_bucket)

        metadata = json.loads(args.metadata_json)

        # 音声ファイルをアップロード
        audio_key = f"podcasts/{args.job_id}/audio.mp3"
        audio_url = r2_client.upload_file(
            args.audio_file, audio_key, content_type="audio/mpeg", public=True
        )

        if r2_custom_domain:
            audio_url = r2_client.generate_public_url(audio_key, r2_custom_domain)

        logger.info(f"Audio uploaded: {audio_url}")

        # メタデータをアップロード
        metadata_key = f"podcasts/{args.job_id}/metadata.json"
        r2_client.upload_json(metadata, metadata_key, public=True)
        logger.info(f"Metadata uploaded: {metadata_key}")

        # RSS を生成・アップロード
        rss_content = generate_rss(metadata, audio_url)
        rss_key = f"podcasts/{args.job_id}/feed.rss"
        # 簡易版: テンポラリファイルに書き込み
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".rss", delete=False) as f:
            f.write(rss_content)
            temp_rss = f.name

        r2_client.upload_file(
            temp_rss, rss_key, content_type="application/rss+xml", public=True
        )
        logger.info(f"RSS feed uploaded: {rss_key}")

        import os as os_module

        os_module.remove(temp_rss)

        # 出力
        output = {
            "status": "success",
            "job_id": args.job_id,
            "audio_url": audio_url,
            "metadata_key": metadata_key,
            "rss_key": rss_key,
        }
        print(json.dumps(output))

    except Exception as e:
        logger.exception(f"Error in upload-job: {e}")
        output = {
            "status": "failed",
            "error": str(e),
        }
        print(json.dumps(output))
        sys.exit(1)


if __name__ == "__main__":
    main()
