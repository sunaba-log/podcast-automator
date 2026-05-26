"""Weekly agenda notification job for Discord.

このモジュールは毎週水曜日 07:00 JST に Cloud Scheduler によって起動され、
ポッドキャスト収録の週次リマインダーを Discord へ投稿します。

Phase 1-A: Discord transcript チャンネルから過去議事録を取得し、
           Episode に再構築して AgendaResult を JSON として出力する検証フェーズ。
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from services.discord_fetcher import DiscordFetcher
from services.notifier import Notifier
from services.transcript_analyzer import AgendaResult, TranscriptAnalyzer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)

DISCORD_WEBHOOK_AGENDA_URL = os.environ.get("DISCORD_WEBHOOK_AGENDA_URL")

# Phase 1-A: Discord transcript channel 設定
_DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
_DISCORD_TRANSCRIPT_CHANNEL_ID = os.environ.get("DISCORD_TRANSCRIPT_CHANNEL_ID")
_TRANSCRIPT_FETCH_LIMIT: int = int(os.environ.get("TRANSCRIPT_FETCH_LIMIT", "50"))
# Cloud Run 上は ephemeral filesystem のため、設定しても次回起動時には消える。
# ローカルデバッグ用途のみを想定しており、本番では基本的に未設定とすること。
_DEBUG_JSON_PATH = os.environ.get("DEBUG_JSON_PATH")

AGENDA_MESSAGE = (
    "📅 **今週の収録リマインダー**\n\n"
    "今週のポッドキャスト収録の準備はできていますか?\n\n"
    "収録後は音声ファイルを GCS にアップロードしてください 🎙️"
)


def _fetch_and_reconstruct() -> tuple[AgendaResult | None, list[str]]:
    """Discord transcript チャンネルからメッセージを取得して Episode を再構築する.

    DISCORD_BOT_TOKEN / DISCORD_TRANSCRIPT_CHANNEL_ID が未設定の場合は (None, []) を返す。

    Returns:
        (result, warnings) のタプル。
        result: AgendaResult。Bot Token / Channel ID 未設定時は None。
        warnings: reconstruct_episodes() が収集した警告メッセージ。
    """
    if not _DISCORD_BOT_TOKEN or not _DISCORD_TRANSCRIPT_CHANNEL_ID:
        logger.info(
            "DISCORD_BOT_TOKEN / DISCORD_TRANSCRIPT_CHANNEL_ID が未設定のため transcript 取得をスキップします。",
        )
        return None, []

    fetcher = DiscordFetcher(bot_token=_DISCORD_BOT_TOKEN)
    messages = fetcher.fetch_messages(
        channel_id=_DISCORD_TRANSCRIPT_CHANNEL_ID,
        limit=_TRANSCRIPT_FETCH_LIMIT,
    )
    logger.info("Fetched %d messages from transcript channel.", len(messages))

    analyzer = TranscriptAnalyzer()
    episodes, warnings = analyzer.reconstruct_episodes(messages)
    logger.info(
        "Reconstructed %d episodes (warnings=%d).",
        len(episodes),
        len(warnings),
    )
    for w in warnings:
        logger.warning("  [transcript] %s", w)

    generated_at = datetime.now(UTC).isoformat()
    result = analyzer.build_agenda(
        episodes=episodes,
        recurring_themes=[],
        action_items=[],
        discussion_prompts=[],
        generated_at=generated_at,
        analysis_window_size=_TRANSCRIPT_FETCH_LIMIT,
        fetched_message_count=len(messages),
    )
    return result, warnings


def _export_debug_json(result: AgendaResult, path: str) -> None:
    """AgendaResult を JSON ファイルとして書き出す.

    Args:
        result: 書き出す AgendaResult。
        path: 出力先ファイルパス。親ディレクトリが存在しない場合は自動作成する。
    """
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Debug JSON written to %s", path)


def send_weekly_agenda() -> None:
    """毎週水曜日に Discord へアジェンダを投稿する."""
    logger.info("## Weekly Agenda Job Start ##")

    # webhook URL は mandatory。未設定は設定ミスとして即 fail させる。
    if not DISCORD_WEBHOOK_AGENDA_URL:
        msg = "DISCORD_WEBHOOK_AGENDA_URL is not set."
        raise RuntimeError(msg)

    logger.info("DISCORD_WEBHOOK_AGENDA_URL configured: %s", bool(DISCORD_WEBHOOK_AGENDA_URL))

    # Phase 1-A: transcript 取得・Episode 再構築
    # 失敗しても reminder 通知自体は継続するため try/except で隔離する
    result: AgendaResult | None = None
    try:
        result, _warnings = _fetch_and_reconstruct()
    except Exception:
        logger.exception("Transcript analysis failed. Falling back to fixed-message notification.")

    if result is not None:
        episode_count = len(result.metadata.source_episode_numbers)
        logger.info(
            "AgendaResult: episodes=%d, schema_version=%s",
            episode_count,
            result.schema_version,
        )
        if _DEBUG_JSON_PATH:
            _export_debug_json(result, _DEBUG_JSON_PATH)

    # フォールバック: 固定文メッセージを Discord へ投稿する
    notifier = Notifier(discord_webhook_url=DISCORD_WEBHOOK_AGENDA_URL)
    success = notifier.send_discord_message(
        message=AGENDA_MESSAGE,
        username="Podcast Scheduler",
    )

    if success:
        logger.info("Weekly agenda sent to Discord successfully.")
    else:
        logger.error("Failed to send weekly agenda to Discord.")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    send_weekly_agenda()


if __name__ == "__main__":
    main()
