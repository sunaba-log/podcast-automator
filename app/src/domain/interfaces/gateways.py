"""Domain interfaces for external systems."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from domain.models import AgendaResult, DiscordMessage, NewsItem, Summary, TopicMatch


class TranscriptProvider(Protocol):
    """Provides transcript generation and summarization."""

    def generate_transcript(self, source_uri: str, model_id: str | None = None) -> str | None:
        """Generate transcript text from an audio URI."""

    def summarize_transcript(
        self,
        transcript: str,
        prompt: str | None = None,
        model_id: str | None = None,
    ) -> Summary:
        """Generate a structured summary from transcript text."""


class ObjectStorage(Protocol):
    """Abstraction for object storage operations."""

    def download_file(self, remote_key: str) -> bytes:
        """Download object bytes by key."""

    def upload_file(
        self,
        file_content: bytes,
        remote_key: str,
        content_type: str,
        *,
        public: bool = True,
    ) -> None:
        """Upload object bytes by key."""

    def generate_public_url(self, remote_key: str, custom_domain: str | None = None) -> str:
        """Generate a public URL for an object key."""


class BlobSource(Protocol):
    """Abstraction for reading source blobs."""

    def download_blob_as_bytes(self, bucket_name: str, blob_name: str) -> bytes:
        """Read raw bytes from blob storage."""


class SecretProvider(Protocol):
    """Abstraction for secret resolution."""

    def get_r2_credentials(self) -> tuple[str, str]:
        """Return R2 access key and secret key."""

    def get_discord_webhook_url(self) -> str | None:
        """Return webhook URL when configured."""


class NotificationGateway(Protocol):
    """Abstraction for outbound notifications."""

    def send_discord_message(self, message: str) -> bool:
        """Send a message and return whether the message was accepted."""


class DiscordTranscriptSource(Protocol):
    """Abstraction for loading Discord messages."""

    def fetch_messages(self, channel_id: str, limit: int = 50) -> list[DiscordMessage]:
        """Fetch Discord messages ordered by recency."""


class NewsSource(Protocol):
    """Abstraction for collecting news items."""

    def fetch_all(self, sources: Sequence[object]) -> list[NewsItem]:
        """Fetch news from configured sources."""


class NewsResearcher(Protocol):
    """Abstraction for AI-assisted news research."""

    def research_news_for_themes(
        self,
        recurring_themes: list[TopicMatch],
        model_id: str,
        per_theme_limit: int = 1,
    ) -> str:
        """Generate a research summary for recurring themes."""


class AgendaSerializer(Protocol):
    """Abstraction for serializing agenda outputs."""

    def to_payload(self, agenda_result: AgendaResult) -> dict:
        """Serialize agenda output for storage or transport."""
