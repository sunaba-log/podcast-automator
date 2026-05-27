"""news_relevance のユニットテスト."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from services.news_fetcher import NewsItem
from services.news_relevance import (
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_SCORE_THRESHOLD,
    KeywordScoringStrategy,
    NewsCandidate,
    NewsScoringStrategy,
    _dedup_by_url,
    _filter_candidates,
    _kw_in_text,
    _normalize_url,
    _sort_candidates,
    match_news_to_agenda,
)
from services.transcript_analyzer import (
    AgendaMetadata,
    AgendaResult,
    TopicMatch,
)

# ── Fixtures / Helpers ─────────────────────────────────────────────────────────

_DT_BASE = datetime(2024, 1, 10, 12, 0, 0, tzinfo=UTC)
_DT_OLDER = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
_DT_NEWER = datetime(2024, 1, 20, 0, 0, 0, tzinfo=UTC)


def _make_news_item(
    title: str = "Test Article",
    url: str = "https://example.com/article",
    summary: str | None = None,
    published_at: datetime | None = None,
    source: str = "TestSource",
) -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        source=source,
        published_at=published_at or _DT_BASE,
        summary=summary,
    )


def _make_topic_match(
    topic_id: str = "test-topic",
    display_name: str = "Test Topic",
    keywords: list[str] | None = None,
    episode_count: int = 1,
    mention_count: int = 1,
) -> TopicMatch:
    return TopicMatch(
        topic_id=topic_id,
        display_name=display_name,
        episode_count=episode_count,
        mention_count=mention_count,
        evidence=[],
        keywords=keywords if keywords is not None else [],
    )


def _make_agenda_result(themes: list[TopicMatch] | None = None) -> AgendaResult:
    metadata = AgendaMetadata(
        generated_at="2024-01-10T12:00:00+00:00",
        source_episode_numbers=[1],
        sort_policy="continuity",
        analysis_window_size=50,
        fetched_message_count=10,
    )
    return AgendaResult(
        metadata=metadata,
        analyzed_episodes=1,
        recurring_themes=themes or [],
        action_items=[],
        discussion_prompts=[],
    )


def _make_candidate(
    title: str = "Test",
    url: str = "https://example.com/article",
    score: float = 0.5,
    matched_keywords: list[str] | None = None,
    published_at: datetime | None = None,
    keywords: list[str] | None = None,
) -> NewsCandidate:
    return NewsCandidate(
        news_item=_make_news_item(title=title, url=url, published_at=published_at),
        topic_match=_make_topic_match(keywords=keywords or []),
        score=score,
        matched_keywords=matched_keywords or [],
    )


# ── TestNewsCandidate ──────────────────────────────────────────────────────────


class TestNewsCandidate:
    def test_fields(self):
        news_item = _make_news_item()
        topic_match = _make_topic_match()
        candidate = NewsCandidate(
            news_item=news_item,
            topic_match=topic_match,
            score=0.75,
            matched_keywords=["AI", "LLM"],
        )
        assert candidate.news_item is news_item
        assert candidate.topic_match is topic_match
        assert candidate.score == 0.75
        assert candidate.matched_keywords == ["AI", "LLM"]

    def test_matched_keywords_defaults_to_empty_list(self):
        candidate = NewsCandidate(
            news_item=_make_news_item(),
            topic_match=_make_topic_match(),
            score=0.5,
        )
        assert candidate.matched_keywords == []


# ── TestKwInText ───────────────────────────────────────────────────────────────


class TestKwInText:
    """_kw_in_text() のユニットテスト.

    マッチ戦略の分岐を検証する:
    - ASCII single-word → word-boundary マッチ
    - フレーズ (スペースを含む) → substring マッチ (変更なし)
    - 日本語など非 ASCII → substring マッチ (変更なし)
    """

    # ── ASCII single-word: word-boundary matching ──────────────────────────────

    def test_ascii_word_matches_standalone(self):
        """ASCII 単語が単独で出現する場合にマッチする."""
        assert _kw_in_text("ai", "ai chip news") is True

    def test_ai_does_not_match_in_airport(self):
        """'ai' が 'airport' の部分文字列としてマッチしない (core regression test)."""
        assert _kw_in_text("ai", "airport runway infrastructure") is False

    def test_ai_does_not_match_in_trail(self):
        """'ai' が 'trail' の部分文字列としてマッチしない."""
        assert _kw_in_text("ai", "trail running competition 2024") is False

    def test_ai_does_not_match_in_detailed(self):
        """'ai' が 'detailed' の部分文字列としてマッチしない."""
        assert _kw_in_text("ai", "detailed analysis report") is False

    def test_ai_does_not_match_in_rain(self):
        """'ai' が 'rain' の部分文字列としてマッチしない."""
        assert _kw_in_text("ai", "heavy rain forecast") is False

    def test_llm_matches_standalone(self):
        """'llm' が単独で出現する場合にマッチする."""
        assert _kw_in_text("llm", "llm based chatbot deployment") is True

    def test_gcp_matches_standalone(self):
        """'gcp' が単独で出現する場合にマッチする."""
        assert _kw_in_text("gcp", "deploy to gcp environment") is True

    def test_bot_does_not_match_in_robot(self):
        """'bot' が 'robot' の部分文字列としてマッチしない."""
        assert _kw_in_text("bot", "robot automation system") is False

    def test_ascii_word_matches_at_sentence_start(self):
        """文頭の ASCII 単語にマッチする."""
        assert _kw_in_text("ai", "ai is transforming the industry") is True

    def test_ascii_word_matches_at_sentence_end(self):
        """文末の ASCII 単語にマッチする."""
        assert _kw_in_text("ai", "the future of ai") is True

    def test_ascii_word_matches_surrounded_by_punctuation(self):
        """句読点に囲まれた ASCII 単語にマッチする."""
        assert _kw_in_text("ai", "next-gen ai: what's coming") is True

    def test_terraform_matches_standalone(self):
        """長い ASCII 単語 (Terraform) も word-boundary でマッチする."""
        assert _kw_in_text("terraform", "terraform deployment guide") is True

    def test_empty_text_returns_false(self):
        """テキストが空文字列の場合は False を返す."""
        assert _kw_in_text("ai", "") is False

    def test_exact_full_text_match(self):
        """テキストがキーワードと完全一致する場合にマッチする."""
        assert _kw_in_text("ai", "ai") is True

    # ── Phrase keywords: substring matching (unchanged) ────────────────────────

    def test_phrase_keyword_matches_in_text(self):
        """スペースを含むフレーズキーワードは substring マッチを使用する."""
        assert _kw_in_text("cloud run", "deploy on cloud run service") is True

    def test_phrase_keyword_no_match(self):
        """フレーズキーワードがテキストに含まれない場合は False."""
        assert _kw_in_text("cloud run", "kubernetes deployment") is False

    # ── Non-ASCII (Japanese): substring matching (unchanged) ──────────────────

    def test_japanese_keyword_matches_substring(self):
        """日本語キーワードは substring マッチを使用する."""
        assert _kw_in_text("モデル", "大規模モデルの評価") is True

    def test_japanese_keyword_matches_in_compound_word(self):
        """日本語は単語境界がないため compound word (ビジネスモデル) にもマッチする."""
        assert _kw_in_text("モデル", "ビジネスモデル変革") is True

    def test_japanese_keyword_no_match(self):
        """日本語キーワードがテキストに含まれない場合は False."""
        assert _kw_in_text("モデル", "機械学習のベンチマーク") is False


# ── TestNormalizeUrl ───────────────────────────────────────────────────────────


class TestNormalizeUrl:
    def test_removes_query_string(self):
        assert _normalize_url("https://example.com/article?utm_source=hn&ref=rss") == "https://example.com/article"

    def test_removes_fragment(self):
        assert _normalize_url("https://example.com/article#section1") == "https://example.com/article"

    def test_removes_query_and_fragment(self):
        assert _normalize_url("https://example.com/a?q=1#top") == "https://example.com/a"

    def test_removes_trailing_slash(self):
        assert _normalize_url("https://example.com/article/") == "https://example.com/article"

    def test_empty_string_returns_empty(self):
        assert _normalize_url("") == ""

    def test_preserves_path(self):
        assert _normalize_url("https://example.com/a/b/c") == "https://example.com/a/b/c"

    def test_http_and_https_are_different(self):
        assert _normalize_url("http://example.com/a") != _normalize_url("https://example.com/a")

    def test_preserves_netloc(self):
        result = _normalize_url("https://news.ycombinator.com/item?id=12345")
        assert result == "https://news.ycombinator.com/item"

    def test_idempotent(self):
        url = "https://example.com/path/to/article"
        assert _normalize_url(_normalize_url(url)) == _normalize_url(url)


# ── TestKeywordScoringStrategy ─────────────────────────────────────────────────


class TestKeywordScoringStrategy:
    def _scorer(self) -> KeywordScoringStrategy:
        return KeywordScoringStrategy()

    def test_empty_keywords_returns_zero(self):
        scorer = self._scorer()
        news = _make_news_item(title="Terraform deployment on GCP")
        topic = _make_topic_match(keywords=[])
        score, matched = scorer.score(news, topic)
        assert score == 0.0
        assert matched == []

    def test_title_match_returns_positive_score(self):
        scorer = self._scorer()
        news = _make_news_item(title="Terraform deployment on GCP")
        topic = _make_topic_match(keywords=["Terraform"])
        score, matched = scorer.score(news, topic)
        assert score > 0.0
        assert "Terraform" in matched

    def test_summary_only_match_returns_positive_score(self):
        scorer = self._scorer()
        news = _make_news_item(title="Cloud updates", summary="Terraform is great for infrastructure")
        topic = _make_topic_match(keywords=["Terraform"])
        score, matched = scorer.score(news, topic)
        assert score > 0.0
        assert "Terraform" in matched

    def test_title_match_scores_higher_than_summary_only(self):
        scorer = self._scorer()
        kw = "Terraform"
        topic = _make_topic_match(keywords=[kw])

        news_title = _make_news_item(title=f"All about {kw}", summary=None)
        news_summary = _make_news_item(title="Cloud updates", summary=f"We use {kw} here")

        score_title, _ = scorer.score(news_title, topic)
        score_summary, _ = scorer.score(news_summary, topic)

        assert score_title > score_summary

    def test_case_insensitive_matching_title(self):
        scorer = self._scorer()
        news = _make_news_item(title="TERRAFORM and gcp news")
        topic = _make_topic_match(keywords=["Terraform", "GCP"])
        score, matched = scorer.score(news, topic)
        assert score > 0.0
        assert set(matched) == {"Terraform", "GCP"}

    def test_case_insensitive_matching_summary(self):
        scorer = self._scorer()
        news = _make_news_item(title="Tech news", summary="TERRAFORM deployed to GCP cluster")
        topic = _make_topic_match(keywords=["Terraform", "GCP"])
        score, _matched = scorer.score(news, topic)
        assert score > 0.0

    def test_no_match_returns_zero(self):
        scorer = self._scorer()
        news = _make_news_item(title="Sports news", summary="Football match results")
        topic = _make_topic_match(keywords=["Terraform", "GCP", "Cloud Run"])
        score, matched = scorer.score(news, topic)
        assert score == 0.0
        assert matched == []

    def test_all_keywords_match_in_title_gives_max_score(self):
        scorer = self._scorer()
        news = _make_news_item(title="Terraform GCP Cloud Run deployment")
        topic = _make_topic_match(keywords=["Terraform", "GCP", "Cloud Run"])
        score, matched = scorer.score(news, topic)
        assert score == 1.0
        assert matched == ["Terraform", "GCP", "Cloud Run"]

    def test_all_keywords_summary_only_gives_half_max(self):
        # summary-only は title の半分の重み → 全マッチでも score = 0.5
        scorer = self._scorer()
        news = _make_news_item(title="Tech news", summary="Terraform GCP Cloud Run all here")
        topic = _make_topic_match(keywords=["Terraform", "GCP", "Cloud Run"])
        score, matched = scorer.score(news, topic)
        assert score == pytest.approx(0.5)
        assert len(matched) == 3

    def test_partial_match_intermediate_score(self):
        scorer = self._scorer()
        # 2 keywords, 1 matches in title → score = (1*2 + 0) / (2*2) = 0.5
        news = _make_news_item(title="Terraform news", summary="Nothing relevant here")
        topic = _make_topic_match(keywords=["Terraform", "GCP"])
        score, _ = scorer.score(news, topic)
        assert score == pytest.approx(0.5)

    def test_summary_none_does_not_crash(self):
        scorer = self._scorer()
        news = _make_news_item(title="Tech news", summary=None)
        topic = _make_topic_match(keywords=["Terraform"])
        # summary=None の場合は空文字扱い → title のみで検索
        score, matched = scorer.score(news, topic)
        assert isinstance(score, float)
        assert isinstance(matched, list)

    def test_matched_keywords_in_definition_order(self):
        # matched_keywords は topic.keywords の定義順
        scorer = self._scorer()
        news = _make_news_item(title="Terraform GCP Cloud Run all in one")
        topic = _make_topic_match(keywords=["Cloud Run", "GCP", "Terraform"])
        _, matched = scorer.score(news, topic)
        # 定義順: Cloud Run → GCP → Terraform
        assert matched == ["Cloud Run", "GCP", "Terraform"]

    def test_duplicate_keywords_both_counted(self):
        # DEFAULT_SEED_TOPICS に "Terraform" と "terraform" が両方存在するケースを模倣
        scorer = self._scorer()
        news = _make_news_item(title="Terraform deployment guide")
        topic = _make_topic_match(keywords=["Terraform", "terraform"])
        score, matched = scorer.score(news, topic)
        # 両方ともマッチ (case-insensitive) → 両方が title ヒット
        assert score == 1.0
        assert "Terraform" in matched
        assert "terraform" in matched

    def test_keyword_in_both_title_and_summary_counted_as_title_hit(self):
        # title と summary 両方に含まれる場合は title ヒット (2x) で扱う
        scorer = self._scorer()
        news = _make_news_item(title="Terraform intro", summary="Terraform is useful")
        # 1 keyword, in both title and summary
        # title ヒット: 1, summary_only: 0 → score = (1*2) / (1*2) = 1.0
        topic = _make_topic_match(keywords=["Terraform"])
        score, matched = scorer.score(news, topic)
        assert score == 1.0
        assert matched == ["Terraform"]

    def test_score_bounded_between_zero_and_one(self):
        scorer = self._scorer()
        news = _make_news_item(title="Terraform GCP Cloud Run all in title", summary="also Terraform GCP Cloud Run")
        topic = _make_topic_match(keywords=["Terraform", "GCP", "Cloud Run"])
        score, _ = scorer.score(news, topic)
        assert 0.0 <= score <= 1.0

    def test_ai_keyword_does_not_match_airport_title(self):
        """'AI' キーワードが 'airport' タイトルに誤マッチしないことを検証 (word-boundary regression).

        旧実装: "ai" in "airport" → True (誤ヒット)
        新実装: re.search(r'\\bai\\b', "airport ...") → None (正しい動作)
        """
        scorer = self._scorer()
        news = _make_news_item(title="Airport runway infrastructure overhaul detailed")
        topic = _make_topic_match(keywords=["AI", "LLM", "Gemini", "Claude", "モデル", "プロンプト"])
        score, matched = scorer.score(news, topic)
        assert score == 0.0
        assert matched == []

    def test_ai_keyword_matches_in_ai_article(self):
        """'AI' キーワードが AI 記事に正しくマッチすることを確認 (word-boundary は正当なマッチを妨げない)."""
        scorer = self._scorer()
        news = _make_news_item(title="New AI model beats GPT-4 on coding benchmarks")
        topic = _make_topic_match(keywords=["AI"])
        score, matched = scorer.score(news, topic)
        assert score > 0.0
        assert "AI" in matched

    def test_bot_keyword_does_not_match_robot_title(self):
        """'Bot' キーワードが 'robot' タイトルに誤マッチしないことを検証 (word-boundary regression)."""
        scorer = self._scorer()
        news = _make_news_item(title="Robot automation advances in manufacturing")
        topic = _make_topic_match(keywords=["Bot"])
        score, matched = scorer.score(news, topic)
        assert score == 0.0
        assert matched == []


# ── TestDeduplicateByUrl ───────────────────────────────────────────────────────


class TestDeduplicateByUrl:
    def test_same_url_different_topics_keeps_highest_score(self):
        url = "https://example.com/article"
        c_low = _make_candidate(url=url, score=0.3)
        c_high = _make_candidate(url=url, score=0.8)
        result = _dedup_by_url([c_low, c_high])
        assert len(result) == 1
        assert result[0].score == 0.8

    def test_same_url_highest_score_wins_regardless_of_order(self):
        url = "https://example.com/article"
        c_high = _make_candidate(url=url, score=0.9)
        c_low = _make_candidate(url=url, score=0.2)
        # 高スコアが先でも後でも同じ結果
        result1 = _dedup_by_url([c_high, c_low])
        result2 = _dedup_by_url([c_low, c_high])
        assert len(result1) == 1
        assert len(result2) == 1
        assert result1[0].score == 0.9
        assert result2[0].score == 0.9

    def test_different_urls_all_kept(self):
        c1 = _make_candidate(url="https://example.com/a", score=0.5)
        c2 = _make_candidate(url="https://example.com/b", score=0.3)
        result = _dedup_by_url([c1, c2])
        assert len(result) == 2

    def test_query_string_deduped_with_clean_url(self):
        # クエリパラメータが異なっても同一 URL とみなす
        c_clean = _make_candidate(url="https://example.com/article", score=0.4)
        c_query = _make_candidate(url="https://example.com/article?utm_source=hn", score=0.7)
        result = _dedup_by_url([c_clean, c_query])
        assert len(result) == 1
        assert result[0].score == 0.7

    def test_trailing_slash_deduped(self):
        c1 = _make_candidate(url="https://example.com/article", score=0.5)
        c2 = _make_candidate(url="https://example.com/article/", score=0.3)
        result = _dedup_by_url([c1, c2])
        assert len(result) == 1
        assert result[0].score == 0.5

    def test_empty_candidates_returns_empty(self):
        assert _dedup_by_url([]) == []

    def test_equal_score_keeps_first_encountered(self):
        url = "https://example.com/article"
        c1 = _make_candidate(url=url, score=0.5, title="First")
        c2 = _make_candidate(url=url, score=0.5, title="Second")
        result = _dedup_by_url([c1, c2])
        assert len(result) == 1
        assert result[0].news_item.title == "First"


# ── TestSortCandidates ─────────────────────────────────────────────────────────


class TestSortCandidates:
    def test_sorted_by_score_descending(self):
        c_low = _make_candidate(score=0.2)
        c_mid = _make_candidate(score=0.5)
        c_high = _make_candidate(score=0.9)
        result = _sort_candidates([c_mid, c_low, c_high])
        scores = [c.score for c in result]
        assert scores == [0.9, 0.5, 0.2]

    def test_same_score_sorted_by_published_at_descending(self):
        c_old = _make_candidate(score=0.5, published_at=_DT_OLDER, url="https://example.com/a")
        c_new = _make_candidate(score=0.5, published_at=_DT_NEWER, url="https://example.com/b")
        result = _sort_candidates([c_old, c_new])
        assert result[0].news_item.published_at == _DT_NEWER
        assert result[1].news_item.published_at == _DT_OLDER

    def test_same_score_same_date_sorted_by_url_ascending(self):
        dt = _DT_BASE
        c_z = _make_candidate(score=0.5, published_at=dt, url="https://z.com/article")
        c_a = _make_candidate(score=0.5, published_at=dt, url="https://a.com/article")
        c_m = _make_candidate(score=0.5, published_at=dt, url="https://m.com/article")
        result = _sort_candidates([c_z, c_a, c_m])
        urls = [c.news_item.url for c in result]
        assert urls == ["https://a.com/article", "https://m.com/article", "https://z.com/article"]

    def test_fully_deterministic(self):
        # 同じ入力を別の順序で渡しても同じ出力になる
        candidates = [
            _make_candidate(score=0.3, published_at=_DT_NEWER, url="https://b.com"),
            _make_candidate(score=0.7, published_at=_DT_BASE, url="https://a.com"),
            _make_candidate(score=0.3, published_at=_DT_OLDER, url="https://c.com"),
        ]
        result1 = _sort_candidates(candidates)
        result2 = _sort_candidates(list(reversed(candidates)))
        assert [c.news_item.url for c in result1] == [c.news_item.url for c in result2]

    def test_empty_list_returns_empty(self):
        assert _sort_candidates([]) == []

    def test_single_item_returned(self):
        c = _make_candidate(score=0.5)
        result = _sort_candidates([c])
        assert result == [c]

    def test_does_not_modify_input_list(self):
        c1 = _make_candidate(score=0.2)
        c2 = _make_candidate(score=0.8)
        original = [c1, c2]
        _sort_candidates(original)
        # 元リストは変更されていない
        assert original[0].score == 0.2


# ── TestFilterCandidates ───────────────────────────────────────────────────────


class TestFilterCandidates:
    def test_above_threshold_is_kept(self):
        c = _make_candidate(score=0.5)
        result = _filter_candidates([c], threshold=0.05)
        assert result == [c]

    def test_below_threshold_is_removed(self):
        c = _make_candidate(score=0.01)
        result = _filter_candidates([c], threshold=0.05)
        assert result == []

    def test_equal_to_threshold_is_kept(self):
        c = _make_candidate(score=0.05)
        result = _filter_candidates([c], threshold=0.05)
        assert result == [c]

    def test_all_above_threshold_all_kept(self):
        candidates = [_make_candidate(score=0.1 * i) for i in range(1, 6)]
        result = _filter_candidates(candidates, threshold=0.05)
        assert len(result) == 5

    def test_all_below_threshold_empty_result(self):
        candidates = [_make_candidate(score=0.01), _make_candidate(score=0.02)]
        result = _filter_candidates(candidates, threshold=0.05)
        assert result == []

    def test_empty_input_returns_empty(self):
        assert _filter_candidates([], threshold=0.05) == []

    def test_zero_threshold_keeps_all_with_score_zero(self):
        c = _make_candidate(score=0.0)
        result = _filter_candidates([c], threshold=0.0)
        assert result == [c]


# ── TestMatchNewsToAgenda ──────────────────────────────────────────────────────


class TestMatchNewsToAgenda:
    def test_empty_news_returns_empty(self):
        agenda = _make_agenda_result([_make_topic_match(keywords=["AI"])])
        result = match_news_to_agenda([], agenda)
        assert result == []

    def test_empty_topics_returns_empty(self):
        news = [_make_news_item(title="AI news")]
        agenda = _make_agenda_result([])
        result = match_news_to_agenda(news, agenda)
        assert result == []

    def test_topic_with_no_keywords_is_skipped(self):
        news = [_make_news_item(title="Terraform news")]
        topic_no_kw = _make_topic_match(keywords=[])
        agenda = _make_agenda_result([topic_no_kw])
        result = match_news_to_agenda(news, agenda)
        assert result == []

    def test_no_match_returns_empty(self):
        news = [_make_news_item(title="Sports results today")]
        topic = _make_topic_match(keywords=["Terraform", "GCP"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda(news, agenda)
        assert result == []

    def test_matching_news_is_returned(self):
        news = [_make_news_item(title="Terraform deployment on GCP")]
        topic = _make_topic_match(keywords=["Terraform", "GCP"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda(news, agenda)
        assert len(result) == 1
        assert result[0].news_item.title == "Terraform deployment on GCP"
        assert result[0].score > 0.0

    def test_threshold_filters_low_score_candidates(self):
        # summary にのみ 1/4 のキーワードがマッチ → low score
        news = [_make_news_item(title="Unrelated title", summary="mentions terraform once")]
        topic = _make_topic_match(keywords=["terraform", "GCP", "Cloud Run", "インフラ"])
        agenda = _make_agenda_result([topic])
        # score = (0*2 + 1) / (4*2) = 0.125 → 高い threshold では落ちる
        result = match_news_to_agenda(news, agenda, score_threshold=0.9)
        assert result == []

    def test_max_candidates_limits_results(self):
        news_items = [_make_news_item(title=f"Terraform news {i}", url=f"https://example.com/{i}") for i in range(20)]
        topic = _make_topic_match(keywords=["Terraform"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda(news_items, agenda, max_candidates=5)
        assert len(result) <= 5

    def test_cross_topic_dedup_keeps_highest_score(self):
        # 同じ URL が 2 つのトピックにマッチ → 最高スコアのトピックのみ残る
        url = "https://example.com/article"
        news = [_make_news_item(title="Terraform GCP deployment", url=url)]

        # topic_a は 1 keyword マッチ (Terraform のみ)
        topic_a = _make_topic_match(topic_id="infra", keywords=["Terraform", "AWS", "Azure"])
        # topic_b は 2 keyword マッチ (Terraform + GCP) → score が高い
        topic_b = _make_topic_match(topic_id="gcp", keywords=["GCP", "Terraform"])

        agenda = _make_agenda_result([topic_a, topic_b])
        result = match_news_to_agenda(news, agenda, score_threshold=0.0)

        # 同一 URL は 1 件のみ
        assert len(result) == 1
        # 高スコアのトピック (topic_b) が選ばれる
        assert result[0].topic_match.topic_id == "gcp"

    def test_result_sorted_by_score_descending(self):
        news_items = [
            _make_news_item(title="Terraform GCP Cloud Run article", url="https://example.com/1"),
            _make_news_item(title="Terraform only article", url="https://example.com/2"),
        ]
        topic = _make_topic_match(keywords=["Terraform", "GCP", "Cloud Run"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda(news_items, agenda, score_threshold=0.0)
        # 3 keyword マッチ(1番) > 1 keyword マッチ(2番)
        assert len(result) == 2
        assert result[0].score >= result[1].score

    def test_result_sorted_by_published_at_when_same_score(self):
        # 同スコアの場合は published_at 降順
        news_old = _make_news_item(
            title="Terraform news",
            url="https://example.com/old",
            published_at=_DT_OLDER,
        )
        news_new = _make_news_item(
            title="Terraform news",
            url="https://example.com/new",
            published_at=_DT_NEWER,
        )
        topic = _make_topic_match(keywords=["Terraform"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda([news_old, news_new], agenda, score_threshold=0.0)
        assert len(result) == 2
        assert result[0].news_item.published_at == _DT_NEWER

    def test_result_sorted_by_url_as_final_tiebreaker(self):
        # score も published_at も同じ場合は url 昇順
        dt = _DT_BASE
        news_z = _make_news_item(title="Terraform", url="https://z.com/a", published_at=dt)
        news_a = _make_news_item(title="Terraform", url="https://a.com/a", published_at=dt)
        topic = _make_topic_match(keywords=["Terraform"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda([news_z, news_a], agenda, score_threshold=0.0)
        assert len(result) == 2
        assert result[0].news_item.url == "https://a.com/a"
        assert result[1].news_item.url == "https://z.com/a"

    def test_title_only_match_returns_candidate(self):
        news = [_make_news_item(title="Terraform intro", summary=None)]
        topic = _make_topic_match(keywords=["Terraform"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda(news, agenda)
        assert len(result) == 1
        assert result[0].matched_keywords == ["Terraform"]

    def test_summary_only_match_returns_candidate(self):
        news = [_make_news_item(title="Cloud updates", summary="Terraform is mentioned here")]
        topic = _make_topic_match(keywords=["Terraform"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda(news, agenda, score_threshold=0.0)
        assert len(result) == 1

    def test_custom_strategy_is_used(self):
        class AlwaysOneStrategy:
            def score(self, _news_item: NewsItem, _topic_match: TopicMatch) -> tuple[float, list[str]]:
                return (1.0, ["custom"])

        news = [_make_news_item(title="Unrelated content")]
        topic = _make_topic_match(keywords=["Terraform"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda(news, agenda, strategy=AlwaysOneStrategy())
        assert len(result) == 1
        assert result[0].score == 1.0
        assert result[0].matched_keywords == ["custom"]

    def test_default_strategy_is_keyword_scoring(self):
        news = [_make_news_item(title="Terraform on GCP deployment")]
        topic = _make_topic_match(keywords=["Terraform", "GCP"])
        agenda = _make_agenda_result([topic])
        # strategy=None の場合は KeywordScoringStrategy が使われる
        result = match_news_to_agenda(news, agenda)
        assert len(result) == 1

    def test_returns_list_of_news_candidates(self):
        news = [_make_news_item(title="Terraform GCP guide")]
        topic = _make_topic_match(keywords=["Terraform"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda(news, agenda)
        assert all(isinstance(c, NewsCandidate) for c in result)

    def test_matched_keywords_in_result(self):
        news = [_make_news_item(title="Terraform GCP guide")]
        topic = _make_topic_match(keywords=["Terraform", "GCP", "AWS"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda(news, agenda, score_threshold=0.0)
        assert len(result) == 1
        # Terraform と GCP はマッチ, AWS はマッチしない
        assert "Terraform" in result[0].matched_keywords
        assert "GCP" in result[0].matched_keywords
        assert "AWS" not in result[0].matched_keywords

    def test_duplicate_url_with_query_deduped(self):
        url_clean = "https://example.com/article"
        url_query = "https://example.com/article?utm_source=hn"
        news_clean = _make_news_item(title="Terraform news", url=url_clean)
        news_query = _make_news_item(title="Terraform news", url=url_query)
        topic = _make_topic_match(keywords=["Terraform"])
        agenda = _make_agenda_result([topic])
        result = match_news_to_agenda([news_clean, news_query], agenda, score_threshold=0.0)
        # 同一 URL とみなされて 1 件のみ
        assert len(result) == 1

    def test_default_constants_are_sane(self):
        assert pytest.approx(0.05) == DEFAULT_SCORE_THRESHOLD
        assert DEFAULT_MAX_CANDIDATES == 10


# ── TestNewsScoringStrategyProtocol ───────────────────────────────────────────


class TestNewsScoringStrategyProtocol:
    def test_keyword_scoring_strategy_satisfies_protocol(self):
        # KeywordScoringStrategy が NewsScoringStrategy Protocol を満たすことを確認
        scorer: NewsScoringStrategy = KeywordScoringStrategy()
        news = _make_news_item(title="Terraform news")
        topic = _make_topic_match(keywords=["Terraform"])
        result = scorer.score(news, topic)
        assert isinstance(result, tuple)
        assert len(result) == 2
        score, matched = result
        assert isinstance(score, float)
        assert isinstance(matched, list)
