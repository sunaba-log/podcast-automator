"""Cloud Run Job: Vertex AI で音声ファイルを処理."""

import sys
import os
import argparse
import json
import logging

# Add shared library to path
sys.path.insert(0, "/app/shared")

from shared.ai import VertexAIClient
from shared.logger import logger

logger.info("Starting process-job")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True, help="Job ID")
    parser.add_argument("--audio-file", required=True, help="Local audio file path")
    parser.add_argument(
        "--gcs-uri", required=True, help="GCS URI of audio file (gs://...)"
    )

    args = parser.parse_args()

    project_id = os.getenv("GCP_PROJECT_ID", "your-project")
    location = os.getenv("VERTEX_AI_LOCATION", "asia-northeast1")
    model_name = os.getenv("VERTEX_AI_MODEL", "gemini-1.5-pro")

    try:
        logger.info(f"Processing audio: {args.gcs_uri} with {model_name}")

        ai_client = VertexAIClient(project_id, location, model_name)

        # 音声を分析
        metadata = ai_client.process_audio_file(args.gcs_uri)

        logger.info(f"Analysis completed: {metadata}")

        # 出力を JSON で stdout に出力
        output = {
            "status": "success",
            "job_id": args.job_id,
            "metadata": metadata,
        }
        print(json.dumps(output))

    except Exception as e:
        logger.exception(f"Error in process-job: {e}")
        output = {
            "status": "failed",
            "error": str(e),
        }
        print(json.dumps(output))
        sys.exit(1)


if __name__ == "__main__":
    main()
