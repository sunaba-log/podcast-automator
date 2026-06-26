"""SNS Post domain model."""

from __future__ import annotations

DEFAULT_HASHTAGS = ["#Podcast", "#新着エピソード", "#議事録"]

PLATFORM_LABELS = {
    "apple": "Apple",
    "spotify": "Spotify",
    "amazon": "Amazon",
}


class SnsPost:
    """Represents a scheduled SNS post."""

    def __init__(
        self,
        message: str,
        platform_urls: dict[str, str] | None = None,
        episode_number: int | None = None,
        hashtags: list[str] | None = None,
    ) -> None:
        """Initialize SNS post."""
        self.message = message
        self.platform_urls = platform_urls or {}
        self.episode_number = episode_number
        self.hashtags = hashtags or DEFAULT_HASHTAGS

    def generate_text(self) -> str:
        """Generate full formatted post text."""
        body = self._build_body()
        tags = " ".join(self.hashtags)
        footer = self._build_footer()
        suffix = f"\n{tags}\n{footer}"
        return f"{body}{suffix}"

    def _build_body(self) -> str:
        if self.episode_number is None:
            return self.message
        return f"第{self.episode_number}回\n{self.message}"

    def _build_footer(self) -> str:
        sections = []
        for key, url in self.platform_urls.items():
            if not url:
                continue
            label = PLATFORM_LABELS.get(key, key.capitalize())
            sections.append(f"▼{label}\n{url}")
        return "\n\n".join(sections)
