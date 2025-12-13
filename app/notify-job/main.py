"""Cloud Run Job: 完了/失敗を Discord に通知."""

import sys
import os
import argparse
import json
import logging

# Add shared library to path
sys.path.insert(0, "/app/shared")

from shared.notifier import DiscordNotifier
from shared.logger import logger

logger.info("Starting notify-job")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True, help="Job ID")
    parser.add_argument(
        "--status", required=True, choices=["completed", "failed"], help="Job status"
    )
    parser.add_argument("--message", required=True, help="Notification message")
    parser.add_argument("--output-url", default=None, help="Output URL (if applicable)")
    parser.add_argument("--error", default=None, help="Error message (if failed)")

    args = parser.parse_args()

    try:
        logger.info(f"Sending Discord notification: {args.status}")

        notifier = DiscordNotifier()

        notifier.send_status_update(
            job_id=args.job_id,
            status=args.status,
            message=args.message,
            error=args.error,
            output_url=args.output_url,
        )

        output = {
            "status": "success",
            "job_id": args.job_id,
            "notification_sent": True,
        }
        print(json.dumps(output))

    except Exception as e:
        logger.exception(f"Error in notify-job: {e}")
        output = {
            "status": "failed",
            "error": str(e),
        }
        print(json.dumps(output))
        sys.exit(1)


if __name__ == "__main__":
    main()
