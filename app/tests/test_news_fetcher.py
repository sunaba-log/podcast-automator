"""news_fetcher のユニットテスト."""

from __future__ import annotations

import time
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
import requests

from services.news_fetcher import (
    DEFAULT_RSS_SOURCES,
    NewsFetcher,
    NewsItem,
    RssSource,
    _parse_published_at,
    _strip_html,
)

# ── Fixtures / Helpers ─────────────────────────────────────────────────────────

_RSS_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>Test RSS feed</description>
    {items}
  </channel>
</rss>
"""

_ITEM_FULL = """\
<item>
  <title>Full Article Title</title>
  <link>https://example.com/full</link>
  <description>&lt;p&gt;Article summary with &lt;b&gt;HTML&lt;/b&gt;.&lt;/p&gt;</description>
  <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
</item>
"""

_ITEM_NO_SUMMARY = """\
<item>
  <title>No Summary Article</title>
  <link>https://example.com/no-summary</link>
  <pubDate>Tue, 02 Jan 2024 08:00:00 +0000</pubDate>
</item>
"""

_ITEM_NO_PUBDATE = """\
<item>
  <title>No PubDate Article</title>
  <link>https://example.com/no-pubdate</link>
  <description>Some summary.</description>
</item>
"""

_ITEM_OLDER = """\
<item>
  <title>Older Article</title>
  <link>https://example.com/older</link>
  <pubDate>Sun, 31 Dec 2023 00:00:00 +0000</pubDate>
</item>
"""

_ITEM_NEWER = """\
<item>
  <title>Newer Article</title>
  <link>https://example.com/newer</link>
  <pubDate>Wed, 03 Jan 2024 00:00:00 +0000</pubDate>
</item>
"""

_ITEM_EMPTY_SUMMARY = """\
<item>
  <title>Empty Summary Article</title>
  <link>https://example.com/empty-summary</link>
  <description>   </description>
  <pubDate>Mon, 01 Jan 2024 06:00:00 +0000</pubDate>
</item>
"""


def _make_feed(*items: str) -> bytes:
    """複数の RSS アイテム文字列から feed バイト列を生成する."""
    return _RSS_TEMPLATE.format(items="\n".join(items)).encode()


def _make_empty_feed() -> bytes:
    """エントリ 0 件の feed バイト列を生成する."""
    return _make_feed()


class _StaticHttpClient:
    """テスト用の静的 HTTP クライアント."""

    def __init__(self, content: bytes, *, raise_error: bool = False) -> None:
        self._content = content
        self._raise_error = raise_error

    def get(self, url: str, *, timeout: int = 10) -> bytes:  # noqa: ARG002
        if self._raise_error:
            response = requests.Response()
            response.status_code = 404
            raise requests.HTTPError(response=response)
        return self._content


class _PerSourceHttpClient:
    """ソース URL ごとに異なる content / error を返すテスト用 HTTP クライアント."""

    def __init__(self, mapping: dict[str, bytes | Exception]) -> None:
        self._mapping = mapping

    def get(self, url: str, *, timeout: int = 10) -> bytes:  # noqa: ARG002
        result = self._mapping[url]
        if isinstance(result, Exception):
            raise result
        return result


# ── TestRssSource ──────────────────────────────────────────────────────────────


class TestRssSource:
    """RssSource dataclass のテスト."""

    def test_fields(self):
        """name / url フィールドが正しく設定されること."""
        src = RssSource(name="Test", url="https://example.com/rss")
        assert src.name == "Test"
        assert src.url == "https://example.com/rss"

    def test_frozen(self):
        """frozen dataclass のため変更が FrozenInstanceError になること."""
        src = RssSource(name="Test", url="https://example.com/rss")
        with pytest.raises(FrozenInstanceError):
            src.name = "Other"  # type: ignore[misc]


# ── TestNewsItem ───────────────────────────────────────────────────────────────


class TestNewsItem:
    """NewsItem dataclass のテスト."""

    def test_required_fields(self):
        """必須フィールドが正しく設定されること."""
        now = datetime.now(UTC)
        item = NewsItem(title="T", url="https://example.com", source="S", published_at=now)
        assert item.title == "T"
        assert item.url == "https://example.com"
        assert item.source == "S"
        assert item.published_at == now

    def test_summary_default_none(self):
        """summary のデフォルトが None であること."""
        item = NewsItem(title="T", url="u", source="S", published_at=datetime.now(UTC))
        assert item.summary is None

    def test_summary_optional(self):
        """summary を指定できること."""
        item = NewsItem(title="T", url="u", source="S", published_at=datetime.now(UTC), summary="text")
        assert item.summary == "text"


# ── TestStripHtml ──────────────────────────────────────────────────────────────


class TestStripHtml:
    """_strip_html() のテスト."""

    def test_removes_tags(self):
        """HTML タグが除去されること."""
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_plain_text_unchanged(self):
        """プレーンテキストはそのまま返ること."""
        assert _strip_html("plain text") == "plain text"

    def test_strips_whitespace(self):
        """前後の空白が除去されること."""
        assert _strip_html("  <p>text</p>  ") == "text"

    def test_empty_string(self):
        """空文字列はそのまま空文字列を返すこと."""
        assert _strip_html("") == ""

    def test_only_tags(self):
        """タグのみの場合は空文字列を返すこと."""
        assert _strip_html("<br/><hr/>") == ""


# ── TestParsePublishedAt ───────────────────────────────────────────────────────


class TestParsePublishedAt:
    """_parse_published_at() のテスト."""

    def test_valid_published_parsed(self):
        """published_parsed が存在する場合は UTC datetime を返すこと."""
        # 2024-01-01 12:00:00 UTC を time.struct_time で表現
        struct = time.strptime("2024-01-01 12:00:00", "%Y-%m-%d %H:%M:%S")
        entry = {"published_parsed": struct}
        result = _parse_published_at(entry, "TestSource")
        assert result.tzinfo is not None
        assert result.tzinfo == UTC
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12

    def test_fallback_when_no_published_parsed(self):
        """published_parsed がない場合は現在時刻 (UTC) を返すこと."""
        before = datetime.now(UTC)
        entry = {}
        result = _parse_published_at(entry, "TestSource")
        after = datetime.now(UTC)
        assert result.tzinfo is not None
        assert result.tzinfo == UTC
        assert before <= result <= after

    def test_fallback_when_none(self):
        """published_parsed が None の場合は現在時刻 (UTC) を返すこと."""
        before = datetime.now(UTC)
        entry = {"published_parsed": None}
        result = _parse_published_at(entry, "TestSource")
        after = datetime.now(UTC)
        assert before <= result <= after


# ── TestNewsFetcherFetch ───────────────────────────────────────────────────────


class TestNewsFetcherFetch:
    """NewsFetcher.fetch() のテスト."""

    def _fetcher(self, content: bytes, *, raise_error: bool = False) -> NewsFetcher:
        return NewsFetcher(http_client=_StaticHttpClient(content, raise_error=raise_error))

    def test_returns_news_items(self):
        """valid RSS から NewsItem のリストが返ること."""
        feed = _make_feed(_ITEM_FULL)
        fetcher = self._fetcher(feed)
        items = fetcher.fetch(RssSource(name="TestFeed", url="https://example.com/rss"))
        assert len(items) == 1

    def test_title_url_source(self):
        """title / url / source が正しく設定されること."""
        feed = _make_feed(_ITEM_FULL)
        fetcher = self._fetcher(feed)
        item = fetcher.fetch(RssSource(name="MyFeed", url="https://example.com/rss"))[0]
        assert item.title == "Full Article Title"
        assert item.url == "https://example.com/full"
        assert item.source == "MyFeed"

    def test_summary_html_stripped(self):
        """summary の HTML タグが除去されること."""
        feed = _make_feed(_ITEM_FULL)
        fetcher = self._fetcher(feed)
        item = fetcher.fetch(RssSource(name="F", url="u"))[0]
        assert item.summary is not None
        assert "<" not in item.summary
        assert item.summary == "Article summary with HTML."

    def test_summary_none_when_absent(self):
        """summary 要素がない場合は None が設定されること."""
        feed = _make_feed(_ITEM_NO_SUMMARY)
        fetcher = self._fetcher(feed)
        item = fetcher.fetch(RssSource(name="F", url="u"))[0]
        assert item.summary is None

    def test_summary_none_when_whitespace_only(self):
        """summary が空白のみの場合は None が設定されること."""
        feed = _make_feed(_ITEM_EMPTY_SUMMARY)
        fetcher = self._fetcher(feed)
        item = fetcher.fetch(RssSource(name="F", url="u"))[0]
        assert item.summary is None

    def test_published_at_timezone_aware(self):
        """published_at が UTC timezone-aware datetime であること."""
        feed = _make_feed(_ITEM_FULL)
        fetcher = self._fetcher(feed)
        item = fetcher.fetch(RssSource(name="F", url="u"))[0]
        assert item.published_at.tzinfo is not None
        assert item.published_at.tzinfo == UTC or item.published_at.utcoffset().total_seconds() == 0

    def test_published_at_correct_value(self):
        """published_at が RSS の pubDate と一致すること."""
        feed = _make_feed(_ITEM_FULL)
        fetcher = self._fetcher(feed)
        item = fetcher.fetch(RssSource(name="F", url="u"))[0]
        assert item.published_at.year == 2024
        assert item.published_at.month == 1
        assert item.published_at.day == 1

    def test_fallback_published_at_when_no_pubdate(self):
        """pubDate なしのエントリでも published_at に UTC datetime が設定されること."""
        feed = _make_feed(_ITEM_NO_PUBDATE)
        before = datetime.now(UTC)
        fetcher = self._fetcher(feed)
        item = fetcher.fetch(RssSource(name="F", url="u"))[0]
        after = datetime.now(UTC)
        assert item.published_at.tzinfo is not None
        assert before <= item.published_at <= after

    def test_empty_feed_returns_empty_list(self):
        """エントリが 0 件の feed は空リストを返すこと."""
        fetcher = self._fetcher(_make_empty_feed())
        items = fetcher.fetch(RssSource(name="F", url="u"))
        assert items == []

    def test_http_error_propagates(self):
        """HTTP エラーが requests.HTTPError として伝播すること."""
        fetcher = self._fetcher(b"", raise_error=True)
        with pytest.raises(requests.HTTPError):
            fetcher.fetch(RssSource(name="F", url="https://example.com/rss"))

    def test_multiple_items(self):
        """複数エントリが全件返ること."""
        feed = _make_feed(_ITEM_FULL, _ITEM_NO_SUMMARY, _ITEM_NO_PUBDATE)
        fetcher = self._fetcher(feed)
        items = fetcher.fetch(RssSource(name="F", url="u"))
        assert len(items) == 3


# ── TestNewsFetcherFetchAll ────────────────────────────────────────────────────


class TestNewsFetcherFetchAll:
    """NewsFetcher.fetch_all() のテスト."""

    def test_flattens_multiple_sources(self):
        """複数ソースの結果がフラットに結合されること."""
        src_a = RssSource(name="A", url="https://a.com/rss")
        src_b = RssSource(name="B", url="https://b.com/rss")
        mapping = {
            src_a.url: _make_feed(_ITEM_FULL),
            src_b.url: _make_feed(_ITEM_NO_SUMMARY),
        }
        fetcher = NewsFetcher(http_client=_PerSourceHttpClient(mapping))
        items = fetcher.fetch_all([src_a, src_b])
        assert len(items) == 2
        sources = {item.source for item in items}
        assert sources == {"A", "B"}

    def test_sorted_by_published_at_descending(self):
        """結果が published_at 降順にソートされること."""
        src = RssSource(name="F", url="https://f.com/rss")
        feed = _make_feed(_ITEM_OLDER, _ITEM_NEWER, _ITEM_FULL)
        fetcher = NewsFetcher(http_client=_StaticHttpClient(feed))
        items = fetcher.fetch_all([src])
        dates = [item.published_at for item in items]
        assert dates == sorted(dates, reverse=True)

    def test_partial_failure_skips_failed_source(self):
        """一部ソースが HTTP エラーでも残りの結果が返ること."""
        src_ok = RssSource(name="OK", url="https://ok.com/rss")
        src_fail = RssSource(name="Fail", url="https://fail.com/rss")
        err_response = requests.Response()
        err_response.status_code = 500
        mapping = {
            src_ok.url: _make_feed(_ITEM_FULL),
            src_fail.url: requests.HTTPError(response=err_response),
        }
        fetcher = NewsFetcher(http_client=_PerSourceHttpClient(mapping))
        items = fetcher.fetch_all([src_ok, src_fail])
        assert len(items) == 1
        assert items[0].source == "OK"

    def test_all_sources_fail_returns_empty(self):
        """全ソースが失敗した場合は空リストを返すこと."""
        src = RssSource(name="F", url="https://fail.com/rss")
        fetcher = NewsFetcher(http_client=_StaticHttpClient(b"", raise_error=True))
        items = fetcher.fetch_all([src])
        assert items == []

    def test_empty_sources_list_returns_empty(self):
        """ソースリストが空の場合は空リストを返すこと."""
        fetcher = NewsFetcher(http_client=_StaticHttpClient(_make_empty_feed()))
        items = fetcher.fetch_all([])
        assert items == []


# ── TestDefaultRssSources ──────────────────────────────────────────────────────


class TestDefaultRssSources:
    """DEFAULT_RSS_SOURCES のテスト."""

    def test_not_empty(self):
        """DEFAULT_RSS_SOURCES が空でないこと."""
        assert len(DEFAULT_RSS_SOURCES) > 0

    def test_all_have_name_and_url(self):
        """全ソースに name と url が設定されていること."""
        for src in DEFAULT_RSS_SOURCES:
            assert src.name
            assert src.url.startswith("https://")
