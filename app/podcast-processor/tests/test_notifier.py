import pytest
from unittest.mock import patch, Mock
import sys
from pathlib import Path
from services.notifier import split_message, send_discord_message, DISCORD_MESSAGE_LIMIT

# 親ディレクトリのservicesモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))

WEBHOOK_URL = "https://discordapp.com/api/webhooks/test/test"


class TestSplitMessage:
    """メッセージ分割機能のテストクラス"""

    def test_short_message_not_split(self):
        """2000文字未満のメッセージは分割されない"""
        message = "This is a short message"
        result = split_message(message)
        assert len(result) == 1
        assert result[0] == message

    def test_exact_limit_message(self):
        """ちょうど2000文字のメッセージは分割されない"""
        message = "a" * DISCORD_MESSAGE_LIMIT
        result = split_message(message)
        assert len(result) == 1
        assert result[0] == message

    def test_over_limit_message(self):
        """2000文字を超えるメッセージは分割される"""
        message = "a" * (DISCORD_MESSAGE_LIMIT + 100)
        result = split_message(message)
        assert len(result) == 2
        assert sum(len(msg) for msg in result) == len(message)
        assert all(len(msg) <= DISCORD_MESSAGE_LIMIT for msg in result)

    def test_multiline_message(self):
        """複数行のメッセージは適切に分割される"""
        lines = ["Hello world\n", "This is a test\n"] * 100
        message = "".join(lines)
        result = split_message(message)

        # すべてのメッセージがサイズ制限内か確認
        assert all(len(msg) <= DISCORD_MESSAGE_LIMIT for msg in result)
        # 結合したメッセージが元のメッセージと一致するか確認
        assert "".join(result).replace("\n", "") == message.replace(
            "\n", ""
        )  # 現在の仕様では改行で分割されることは保証されない

    def test_single_very_long_line(self):
        """1行が2000文字を超える場合は分割される"""
        message = "x" * (DISCORD_MESSAGE_LIMIT * 2 + 500)
        result = split_message(message)

        # 正確に3つに分割されることを確認
        assert len(result) == 3
        assert all(len(msg) <= DISCORD_MESSAGE_LIMIT for msg in result)
        assert "".join(result) == message

    def test_custom_max_length(self):
        """カスタム最大文字数で分割される"""
        message = "a" * 300
        result = split_message(message, max_length=100)

        assert len(result) == 3
        assert all(len(msg) <= 100 for msg in result)
        assert "".join(result) == message

    def test_empty_message(self):
        """空のメッセージは空のリストが返される"""
        result = split_message("")
        assert result == [""]

    def test_message_with_newlines_at_boundary(self):
        """改行を含むメッセージが正確に分割される"""
        message = "a" * 1000 + "\n" + "b" * 1000 + "\n" + "c" * 500
        result = split_message(message)

        assert all(len(msg) <= DISCORD_MESSAGE_LIMIT for msg in result)
        assert "".join(result).replace("\n", "") == message.replace("\n", "")


class TestSendDiscordMessage:
    """Discord送信機能のテストクラス"""

    def test_send_short_message_success(self):
        """短いメッセージの送信に成功する"""
        webhook_url = WEBHOOK_URL
        message = "Test message"

        mock_response = Mock()
        mock_response.status_code = 204

        with patch("services.notifier.requests.post", return_value=mock_response) as mock_post:
            result = send_discord_message(webhook_url, message)

            assert result is True
            mock_post.assert_called_once()

    def test_send_long_message_split(self):
        """長いメッセージは複数回に分割して送信される"""
        webhook_url = WEBHOOK_URL
        message = "x" * (DISCORD_MESSAGE_LIMIT * 2 + 500)

        mock_response = Mock()
        mock_response.status_code = 204

        with patch("services.notifier.requests.post", return_value=mock_response) as mock_post:
            result = send_discord_message(webhook_url, message)

            assert result is True
            # 3回のメッセージ送信が呼ばれることを確認
            assert mock_post.call_count == 3

    def test_send_message_with_custom_username(self):
        """カスタムユーザー名で送信される"""
        webhook_url = WEBHOOK_URL
        message = "Test message"
        username = "Custom Bot"

        mock_response = Mock()
        mock_response.status_code = 204

        with patch("services.notifier.requests.post", return_value=mock_response) as mock_post:
            result = send_discord_message(webhook_url, message, username)

            assert result is True
            # ペイロードにカスタムユーザー名が含まれていることを確認
            call_args = mock_post.call_args
            assert call_args[1]["json"]["username"] == username

    def test_send_message_failure(self):
        """送信失敗時はFalseが返される"""
        webhook_url = WEBHOOK_URL
        message = "Test message"

        mock_response = Mock()
        mock_response.status_code = 400  # エラーステータス

        with patch("services.notifier.requests.post", return_value=mock_response):
            result = send_discord_message(webhook_url, message)

            assert result is False

    def test_send_message_exception(self):
        """例外が発生した場合はFalseが返される"""
        webhook_url = WEBHOOK_URL
        message = "Test message"

        with patch("services.notifier.requests.post", side_effect=Exception("Connection error")):
            result = send_discord_message(webhook_url, message)

            assert result is False
