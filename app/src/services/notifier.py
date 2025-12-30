import logging  # noqa: D100

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)

# Discord のメッセージ上限
DISCORD_MESSAGE_LIMIT = 2000


def split_message(message: str, max_length: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """メッセージを指定された最大文字数で分割する.

    Args:
        message: 送信するメッセージ
        max_length: 最大文字数(デフォルト: 2000)

    Returns:
        分割されたメッセージのリスト
    """
    if len(message) <= max_length:
        return [message]

    messages = []
    current_message = ""

    for line in message.split("\n"):
        # 1行が上限を超える場合
        if len(line) > max_length:
            # 現在のメッセージを保存
            if current_message:
                messages.append(current_message)
                current_message = ""

            # 長い行を分割
            for i in range(0, len(line), max_length):
                messages.extend([line[i : i + max_length]])
        else:
            # 現在のメッセージに行を追加
            test_message = current_message + ("\n" if current_message else "") + line

            if len(test_message) <= max_length:
                current_message = test_message
            else:
                # 現在のメッセージを保存して新しいメッセージを開始
                if current_message:
                    messages.append(current_message)
                current_message = line

    # 残りのメッセージを追加
    if current_message:
        messages.append(current_message)

    return messages


class Notifier:
    """通知サービスクライアント."""

    def __init__(self, discord_webhook_url: str | None = None) -> None:
        """通知サービスクライアントを初期化する.

        Args:
            discord_webhook_url: Discord Webhook URL. 指定しない場合は通知が無効化される.
        """
        self.discord_webhook_url = discord_webhook_url

        if self.discord_webhook_url is None:
            logger.warning("Discord Webhook URLが設定されていません。通知機能はスキップされます。")

    def send_discord_message(self, message: str, username: str = "Podcast Automator") -> bool:
        """Discordにメッセージを送信する. 2000文字を超える場合は自動的に分割して送信する.

        URLが設定されていない場合は送信処理を行わずにFalseを返す.

        Args:
            message: 送信するメッセージ
            username: Discordで表示するユーザー名

        Returns:
            送信に成功した場合はTrue, 失敗またはスキップした場合はFalse
        """
        if self.discord_webhook_url is None:
            logger.warning("Discord Webhook URL未設定のため、メッセージ送信をスキップしました: %s...", message[:20])
            return False

        try:
            messages = split_message(message)
            for msg in messages:
                payload = {"username": username, "content": msg}
                response = requests.post(self.discord_webhook_url, json=payload, timeout=10)

                if response.status_code not in (200, 204):
                    logger.error("Discord送信失敗: ステータス %d", response.status_code)
                    return False
            return True

        except Exception:
            logger.exception("Discordメッセージ送信エラー:")
            return False
