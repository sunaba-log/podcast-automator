"""Backward-compatible promoter entrypoint module."""

from entrypoints.promoter_main import auto_post_sns, main

__all__ = ["auto_post_sns", "main"]


if __name__ == "__main__":
    main()
