"""RSS フィードからニュースアイテムを取得するフェッチャー.

設計方針:
- Pure function / small helper 中心。副作用は fetch() / fetch_all() の HTTP 呼び出しのみ。
- 外部 HTTP 呼び出しは HttpGetProtocol に閉じ込め、テスト時に差し替え可能にする。
- feedparser を使って RSS/Atom の差異を吸収する (feedparser は既存依存)。
- published_at は常に UTC timezone-aware datetime として返す。
- agenda_main.py / Terraform / infra への接続は Phase 3-B 以降で行う。
"""

from __future__ import annotations

import logging
import re
from calendar import timegm
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import feedparser
import requests

logger = logging.getLogger(__name__)


# ── Data classes ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RssSource:
    """RSS / Atom フィードのソース設定.

    Attributes:
        name: ソース識別名。NewsItem.source に転写される。
        url: RSS / Atom フィード URL。
    """

    name: str
    url: str


@dataclass
class NewsItem:
    """RSS フィードから取得した 1 ニュースアイテム.

    Attributes:
        title: 記事タイトル。
        url: 記事 URL。
        source: 取得元ソース名 (RssSource.name から転写)。
        published_at: 公開日時 (UTC timezone-aware)。
        summary: 記事の概要テキスト (HTML タグ除去済み)。None の場合は概要なし。
    """

    title: str
    url: str
    source: str
    published_at: datetime
    summary: str | None = None


# ── Default sources ────────────────────────────────────────────────────────────

DEFAULT_RSS_SOURCES: list[RssSource] = [
    RssSource(name="Hacker News", url="https://news.ycombinator.com/rss"),
    RssSource(name="Google Cloud Blog", url="https://cloud.google.com/feeds/gcp-blog-en.xml"),
]


# ── HTTP adapter ───────────────────────────────────────────────────────────────


class HttpGetProtocol(Protocol):
    """HTTP GET リクエストのインターフェース.

    テスト時は静的バイト列を返す実装に差し替えることで、
    外部 HTTP 呼び出しをテストから分離する。
    """

    def get(self, url: str, *, timeout: int = 10) -> bytes:
        """指定 URL へ GET リクエストを送り、レスポンスボディを bytes で返す.

        Args:
            url: リクエスト先 URL。
            timeout: タイムアウト秒数。

        Returns:
            レスポンスボディの bytes。

        Raises:
            requests.HTTPError: HTTP 4xx / 5xx の場合。
        """
        ...  # pragma: no cover


class RequestsHttpClient:
    """requests ライブラリを使った HttpGetProtocol の実装."""

    def get(self, url: str, *, timeout: int = 10) -> bytes:
        """指定 URL へ GET リクエストを送り、レスポンスボディを bytes で返す.

        Args:
            url: リクエスト先 URL。
            timeout: タイムアウト秒数。

        Returns:
            レスポンスボディの bytes。

        Raises:
            requests.HTTPError: HTTP 4xx / 5xx の場合。
        """
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content


# ── Private helpers ────────────────────────────────────────────────────────────


def _strip_html(text: str) -> str:
    """HTML タグを除去してプレーンテキストを返す.

    Args:
        text: HTML タグを含む可能性のある文字列。

    Returns:
        HTML タグを除去し、前後の空白を strip したテキスト。
    """
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_published_at(entry: feedparser.util.FeedParserDict, source_name: str) -> datetime:
    """Feedparser エントリから UTC timezone-aware datetime を生成する.

    feedparser が published_parsed を持つ場合はそれを使い、
    持たない場合は現在時刻 (UTC) を fallback として使用する。

    Args:
        entry: feedparser のエントリオブジェクト。
        source_name: ログ用のソース識別名。

    Returns:
        UTC timezone-aware datetime。
    """
    published_parsed = entry.get("published_parsed")
    if published_parsed is not None:
        return datetime.fromtimestamp(timegm(published_parsed), tz=UTC)

    logger.warning(
        "published_parsed が取得できませんでした。現在時刻を fallback として使用します。 source=%s title=%s",
        source_name,
        entry.get("title", "(no title)"),
    )
    return datetime.now(UTC)


def _entry_to_news_item(
    entry: feedparser.util.FeedParserDict,
    source: RssSource,
) -> NewsItem | None:
    """Feedparser エントリを NewsItem に変換する.

    title または link が空の場合は None を返してスキップする。

    Args:
        entry: feedparser のエントリオブジェクト。
        source: 取得元の RssSource。

    Returns:
        変換した NewsItem。title / link が空の場合は None。
    """
    title: str = (entry.get("title") or "").strip()
    url: str = (entry.get("link") or "").strip()

    if not title or not url:
        logger.debug(
            "title または url が空のエントリをスキップします。source=%s entry=%s",
            source.name,
            entry.get("id", "(no id)"),
        )
        return None

    raw_summary: str | None = entry.get("summary") or entry.get("description")
    summary: str | None = _strip_html(raw_summary) if raw_summary else None
    # strip 後に空文字になった場合も None 扱い
    if summary is not None and not summary:
        summary = None

    published_at = _parse_published_at(entry, source.name)

    return NewsItem(
        title=title,
        url=url,
        source=source.name,
        published_at=published_at,
        summary=summary,
    )


# ── NewsFetcher ────────────────────────────────────────────────────────────────


class NewsFetcher:
    """RSS / Atom フィードからニュースアイテムを取得するクライアント.

    外部 HTTP 呼び出しを HttpGetProtocol に閉じ込めているため、
    テスト時は静的バイト列を返す実装に差し替えることができる。
    """

    def __init__(self, http_client: HttpGetProtocol | None = None) -> None:
        """クライアントを初期化する.

        Args:
            http_client: HTTP GET アダプタ。None の場合は RequestsHttpClient を使用する。
        """
        self._http_client: HttpGetProtocol = http_client if http_client is not None else RequestsHttpClient()

    def fetch(self, source: RssSource) -> list[NewsItem]:
        """1 つの RSS ソースからニュースアイテムを取得する.

        Args:
            source: 取得対象の RssSource。

        Returns:
            NewsItem のリスト。エントリが 0 件の場合は空リスト。

        Raises:
            requests.HTTPError: HTTP 4xx / 5xx の場合。
        """
        raw = self._http_client.get(source.url)
        feed = feedparser.parse(raw)

        items: list[NewsItem] = []
        for entry in feed.entries:
            item = _entry_to_news_item(entry, source)
            if item is not None:
                items.append(item)

        logger.info("Fetched %d items from %s.", len(items), source.name)
        return items

    def fetch_all(
        self,
        sources: list[RssSource],
    ) -> list[NewsItem]:
        """複数の RSS ソースからニュースアイテムをまとめて取得する.

        各ソースで HTTP エラーが発生した場合は warning ログを出力してスキップし、
        成功したソースの結果のみを返す。
        全件を published_at 降順でソートして返す。

        Args:
            sources: 取得対象の RssSource リスト。

        Returns:
            全ソースの NewsItem をまとめた published_at 降順リスト。
            取得に失敗したソースの分は含まれない。
        """
        all_items: list[NewsItem] = []
        for source in sources:
            try:
                items = self.fetch(source)
                all_items.extend(items)
            except Exception:  # noqa: BLE001
                logger.warning("Failed to fetch from %s. Skipping.", source.name, exc_info=True)

        all_items.sort(key=lambda item: item.published_at, reverse=True)
        return all_items
