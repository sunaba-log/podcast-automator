"""DiscordFetcher のユニットテスト."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from services.discord_fetcher import DiscordFetcher, DiscordMessage


def _raw_message(
    *,
    msg_id: str = "1",
    content: str = "hello",
    timestamp: str = "2024-01-01T00:00:00.000Z",
    username: str = "bot",
) -> dict:
    """Discord API レスポンスの生メッセージ辞書を生成するファクトリ."""
    return {
        "id": msg_id,
        "content": content,
        "timestamp": timestamp,
        "author": {"username": username},
    }


class TestDiscordFetcher:
    """DiscordFetcher.fetch_messages() のテストクラス."""

    def test_returns_discord_message_list(self):
        """正常レスポンスが DiscordMessage のリストに変換されること."""
        raw = [_raw_message(msg_id="1", content="test message")]
        mock_resp = MagicMock()
        mock_resp.json.return_value = raw

        with patch("services.discord_fetcher.requests.get", return_value=mock_resp) as mock_get:
            fetcher = DiscordFetcher(bot_token="test-token")
            result = fetcher.fetch_messages(channel_id="ch123", limit=10)

        mock_get.assert_called_once()
        assert len(result) == 1
        assert isinstance(result[0], DiscordMessage)
        assert result[0].id == "1"
        assert result[0].content == "test message"

    def test_bot_prefix_added_to_auth_header(self):
        """Authorization ヘッダーに 'Bot ' プレフィックスが付与されること."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [_raw_message()]

        with patch("services.discord_fetcher.requests.get", return_value=mock_resp) as mock_get:
            fetcher = DiscordFetcher(bot_token="my-secret-token")
            fetcher.fetch_messages(channel_id="ch123")

        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Bot my-secret-token"

    def test_limit_clamped_to_max_100(self):
        """limit が 100 を超える場合に 100 にクランプされること."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = []

        with patch("services.discord_fetcher.requests.get", return_value=mock_resp) as mock_get:
            fetcher = DiscordFetcher(bot_token="tok")
            fetcher.fetch_messages(channel_id="ch", limit=200)

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["limit"] == 100

    def test_limit_clamped_to_min_1(self):
        """limit が 1 未満の場合に 1 にクランプされること."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = []

        with patch("services.discord_fetcher.requests.get", return_value=mock_resp) as mock_get:
            fetcher = DiscordFetcher(bot_token="tok")
            fetcher.fetch_messages(channel_id="ch", limit=0)

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["limit"] == 1

    def test_raises_http_error_on_4xx_5xx(self):
        """API が 4xx/5xx を返した場合に HTTPError が raise されること."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")

        with patch("services.discord_fetcher.requests.get", return_value=mock_resp):
            fetcher = DiscordFetcher(bot_token="tok")
            with pytest.raises(requests.HTTPError):
                fetcher.fetch_messages(channel_id="ch")

    def test_missing_content_field_defaults_to_empty_string(self):
        """content フィールドが欠損しているメッセージが空文字列になること."""
        raw = [{"id": "1", "timestamp": "2024-01-01T00:00:00.000Z", "author": {"username": "bot"}}]
        mock_resp = MagicMock()
        mock_resp.json.return_value = raw

        with patch("services.discord_fetcher.requests.get", return_value=mock_resp):
            fetcher = DiscordFetcher(bot_token="tok")
            result = fetcher.fetch_messages(channel_id="ch")

        assert result[0].content == ""
