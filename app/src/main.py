"""Backward-compatible main module.

The implementation moved to entrypoints.main in Step4.
"""

from entrypoints.main import main, process_podcast_workflow, send_discord_notification

__all__ = ["main", "process_podcast_workflow", "send_discord_notification"]


if __name__ == "__main__":
    main()
