"""Backward-compatible agenda entrypoint module.

The implementation moved to entrypoints.agenda_main in Step4.
"""

from entrypoints.agenda_main import main, send_weekly_agenda

__all__ = ["main", "send_weekly_agenda"]


if __name__ == "__main__":
    main()
