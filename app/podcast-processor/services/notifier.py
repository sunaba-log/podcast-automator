from typing import List
import requests

# Discord のメッセージ上限
DISCORD_MESSAGE_LIMIT = 2000


def split_message(message: str, max_length: int = DISCORD_MESSAGE_LIMIT) -> List[str]:
    """
    メッセージを指定された最大文字数で分割する。

    Args:
        message: 送信するメッセージ
        max_length: 最大文字数（デフォルト: 2000）

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
                messages.append(line[i : i + max_length])
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


def send_discord_message(
    webhook_url: str, message: str, username: str = "Podcast Automator"
) -> bool:
    """
    Discordにメッセージを送信する。
    2000文字を超える場合は自動的に分割して送信する。

    Args:
        webhook_url: Discord Webhook URL
        message: 送信するメッセージ
        username: Discordで表示するユーザー名

    Returns:
        成功したかどうか
    """
    try:
        messages = split_message(message)
        for msg in messages:
            payload = {"username": username, "content": msg}
            response = requests.post(webhook_url, json=payload)
            if response.status_code not in (200, 204):
                print(f"Discord送信失敗: ステータス {response.status_code}")
                return False
        return True

    except Exception as e:
        print(f"Discordメッセージ送信エラー: {str(e)}")
        return False


def send_discord(status: str, title: str = "", error_message: str = ""):
    """Discordへ通知を送信する関数"""
    pass
