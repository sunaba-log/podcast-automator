"""Discord REST API からチャンネルメッセージを取得するクライアント."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

_DISCORD_API_BASE = "https://discord.com/api/v10"
_MAX_FETCH_LIMIT = 100  # Discord API の上限


@dataclass
class DiscordMessage:
    """Discord チャンネルの 1 メッセージ."""

    id: str
    content: str
    timestamp: str  # ISO8601
    author_name: str


class DiscordFetcher:
    """Discord Bot API 経由でチャンネルメッセージを取得するクライアント.

    Bot Token を使って読み取り専用の操作のみ行う。
    Webhook URL とは異なり、メッセージの読み取りに使用する。
    """

    def __init__(self, bot_token: str) -> None:
        """クライアントを初期化する.

        Args:
            bot_token: Discord Bot Token。"Bot " プレフィックスは自動で付与する。
        """
        # strip() で Secret Manager 経由の trailing newline など余分な空白を除去する
        self._headers = {
            "Authorization": f"Bot {bot_token.strip()}",
            "Content-Type": "application/json",
        }

    def fetch_messages(
        self,
        channel_id: str,
        limit: int = 50,
    ) -> list[DiscordMessage]:
        """最新 limit 件のメッセージを新しい順で返す.

        Args:
            channel_id: 取得対象のチャンネル ID。
            limit: 取得件数。1-100 の範囲に自動でクランプされる。

        Returns:
            DiscordMessage のリスト(新しい順)。

        Raises:
            requests.HTTPError: API が 4xx / 5xx を返した場合。
        """
        clamped_limit = min(max(1, limit), _MAX_FETCH_LIMIT)
        if clamped_limit != limit:
            logger.warning(
                "fetch_messages: limit %d clamped to %d (Discord API max=%d)",
                limit,
                clamped_limit,
                _MAX_FETCH_LIMIT,
            )

        url = f"{_DISCORD_API_BASE}/channels/{channel_id}/messages"
        response = requests.get(
            url,
            headers=self._headers,
            params={"limit": clamped_limit},
            timeout=10,
        )
        response.raise_for_status()

        return [
            DiscordMessage(
                id=m["id"],
                content=m.get("content", ""),
                timestamp=m["timestamp"],
                author_name=m["author"]["username"],
            )
            for m in response.json()
        ]
