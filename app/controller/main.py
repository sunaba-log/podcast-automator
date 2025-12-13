"""Cloud Run Service: Eventarc イベント受け取り・Job 起動コントローラ."""

from flask import Flask, request, jsonify
import json
import logging
import uuid
from datetime import datetime
from google.cloud import run_v2
from google.cloud import secretmanager

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/", methods=["POST"])
def handle_event():
    """Eventarc からのイベントを受け取り、fetch-job を起動."""
    try:
        event = request.get_json()
        logger.info(f"Received event: {json.dumps(event)}")

        # イベントからバケット・オブジェクト名を抽出
        bucket = event.get("bucket") or (event.get("data") or {}).get("bucket")
        name = event.get("name") or (event.get("data") or {}).get("name")

        if not bucket or not name:
            logger.warning("Missing bucket or object name in event")
            return jsonify({"error": "invalid event"}), 400

        # ジョブ ID を生成
        job_id = str(uuid.uuid4())

        logger.info(f"Starting fetch-job for {bucket}/{name} (job_id={job_id})")

        # Cloud Run Job (fetch-job) を起動
        response = _execute_job(
            job_name="fetch-job",
            job_args={
                "job_id": job_id,
                "bucket": bucket,
                "object_name": name,
            },
        )

        logger.info(f"Job started: {response}")

        return jsonify(
            {
                "status": "accepted",
                "job_id": job_id,
            }
        ), 202

    except Exception as e:
        logger.exception(f"Error handling event: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """ヘルスチェック."""
    return jsonify({"status": "healthy"}), 200


def _execute_job(job_name: str, job_args: dict) -> dict:
    """Cloud Run Job を実行."""
    import os

    project_id = os.getenv("GCP_PROJECT_ID", "your-project")
    region = os.getenv("GCP_REGION", "asia-northeast1")

    client = run_v2.JobsClient()
    parent = f"projects/{project_id}/locations/{region}"
    job_path = f"{parent}/jobs/{job_name}"

    # ジョブの実行（非同期）
    operation = client.run_job(request={"name": job_path})

    return {
        "job_name": job_name,
        "operation_name": operation.name
        if hasattr(operation, "name")
        else str(operation),
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
