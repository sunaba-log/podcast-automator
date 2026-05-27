"""agenda_formatter のユニットテスト."""

from __future__ import annotations

from datetime import UTC, datetime

from services.agenda_formatter import (
    _MAX_AI_NEWS_SECTION_LENGTH,
    _MAX_MESSAGE_LENGTH,
    _build_ai_news_section,
    _format_episode_refs,
    _truncate,
    format_agenda_message,
)
from services.news_fetcher import NewsItem
from services.news_relevance import NewsCandidate
from services.transcript_analyzer import (
    ActionItem,
    AgendaMetadata,
    AgendaResult,
    DiscussionPrompt,
    MentionEvidence,
    PromptType,
    SortPolicy,
    TopicMatch,
)

# ── Factories ──────────────────────────────────────────────────────────────────


def _make_metadata(
    *,
    analyzed_episodes: int = 2,
    fetched: int = 50,
    source_episodes: list[int] | None = None,
) -> AgendaMetadata:
    return AgendaMetadata(
        generated_at="2024-01-15T00:00:00+00:00",
        source_episode_numbers=source_episodes or list(range(1, analyzed_episodes + 1)),
        sort_policy=str(SortPolicy.continuity),
        analysis_window_size=50,
        fetched_message_count=fetched,
    )


def _make_result(
    *,
    themes: list[TopicMatch] | None = None,
    items: list[ActionItem] | None = None,
    prompts: list[DiscussionPrompt] | None = None,
    analyzed_episodes: int = 2,
    fetched: int = 50,
) -> AgendaResult:
    return AgendaResult(
        metadata=_make_metadata(analyzed_episodes=analyzed_episodes, fetched=fetched),
        analyzed_episodes=analyzed_episodes,
        recurring_themes=themes or [],
        action_items=items or [],
        discussion_prompts=prompts or [],
    )


def _make_theme(
    *,
    topic_id: str = "infra-terraform",
    display_name: str = "インフラ / Terraform",
    episode_count: int = 2,
    mention_count: int = 3,
    evidence_episodes: list[int] | None = None,
) -> TopicMatch:
    ep_list = evidence_episodes or [1, 2]
    evidence = [MentionEvidence(source_episode=ep, text=f"Terraform mention {ep}", sentence_index=0) for ep in ep_list]
    return TopicMatch(
        topic_id=topic_id,
        display_name=display_name,
        episode_count=episode_count,
        mention_count=mention_count,
        evidence=evidence,
        score=float(mention_count),
    )


def _make_item(*, text: str = "TODO: 設定を確認する", source_episode: int = 1) -> ActionItem:
    return ActionItem(text=text, source_episode=source_episode)


def _make_prompt(
    *,
    sentence: str = "このアーキテクチャはどう実装すべきか?",
    prompt_type: PromptType = PromptType.design_decision,
    source_episode: int = 1,
) -> DiscussionPrompt:
    return DiscussionPrompt(
        sentence=sentence,
        prompt_type=prompt_type,
        source_episode=source_episode,
    )


def _make_news_candidate(
    *,
    title: str = "Claude 4 context window expanded to 1M tokens",
    source: str = "Hacker News",
    url: str = "https://news.ycombinator.com/item?id=12345",
    topic_display_name: str = "AI / LLM 活用",
    score: float = 0.5,
) -> NewsCandidate:
    news_item = NewsItem(
        title=title,
        url=url,
        source=source,
        published_at=datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC),
    )
    topic_match = _make_theme(display_name=topic_display_name)
    return NewsCandidate(
        news_item=news_item,
        topic_match=topic_match,
        score=score,
    )


# ── TestFormatAgendaMessage ────────────────────────────────────────────────────


class TestFormatAgendaMessage:
    """format_agenda_message() のテストクラス."""

    def test_header_always_present(self):
        """ヘッダーが常に含まれること."""
        result = _make_result()
        msg = format_agenda_message(result)
        assert "今週の会話のタネ" in msg

    def test_footer_always_present(self):
        """フッター (分析メタデータ) が常に含まれること."""
        result = _make_result(analyzed_episodes=3, fetched=50)
        msg = format_agenda_message(result)
        assert "3 エピソード" in msg
        assert "50 件取得" in msg

    def test_footer_shows_news_count_when_candidates_given(self):
        """news_candidates が渡された場合、フッターにニュース接続件数が表示されること."""
        result = _make_result(analyzed_episodes=11, fetched=50)
        candidates = [_make_news_candidate(), _make_news_candidate(title="Another news")]
        msg = format_agenda_message(result, news_candidates=candidates)
        assert "11 エピソード" in msg
        assert "2 ニュース接続" in msg
        # "件取得" は news あり時は表示しない
        assert "件取得" not in msg

    def test_all_sections_present_when_data_exists(self):
        """全セクションにデータがある場合、テーマ・ニュース・論点セクションが含まれること."""
        result = _make_result(
            themes=[_make_theme()],
            items=[_make_item()],
            prompts=[_make_prompt()],
        )
        candidates = [_make_news_candidate()]
        msg = format_agenda_message(result, news_candidates=candidates, max_items=3)
        assert "最近よく出てきたテーマ" in msg
        assert "最近の会話と繋がりそうなニュース" in msg
        assert "アクションアイテム" in msg
        assert "気になっている問い" in msg

    def test_empty_themes_section_omitted(self):
        """recurring_themes が 0 件の場合、テーマセクションが省略されること."""
        result = _make_result(themes=[], items=[_make_item()])
        msg = format_agenda_message(result)
        assert "最近よく出てきたテーマ" not in msg

    def test_empty_items_section_omitted(self):
        """action_items が 0 件の場合、アクションアイテムセクションが省略されること."""
        result = _make_result(themes=[_make_theme()], items=[])
        msg = format_agenda_message(result, max_items=5)
        assert "アクションアイテム" not in msg

    def test_items_section_omitted_by_default(self):
        """max_items=0 (デフォルト) の場合、アクションアイテムセクションが省略されること."""
        result = _make_result(themes=[_make_theme()], items=[_make_item()])
        msg = format_agenda_message(result)  # max_items=0 がデフォルト
        assert "アクションアイテム" not in msg

    def test_empty_prompts_section_omitted(self):
        """discussion_prompts が 0 件の場合、論点セクションが省略されること."""
        result = _make_result(themes=[_make_theme()], prompts=[])
        msg = format_agenda_message(result)
        assert "気になっている問い" not in msg

    def test_all_empty_shows_only_header_and_footer(self):
        """全セクション空の場合、ヘッダーとフッターのみ含まれること."""
        result = _make_result()
        msg = format_agenda_message(result)
        assert "今週の会話のタネ" in msg
        assert "エピソード" in msg
        assert "最近よく出てきたテーマ" not in msg
        assert "アクションアイテム" not in msg
        assert "気になっている問い" not in msg

    def test_max_themes_limit_applied(self):
        """max_themes を超えるテーマが切り捨てられること."""
        themes = [_make_theme(topic_id=f"t{i}", display_name=f"Topic {i}") for i in range(10)]
        result = _make_result(themes=themes)
        msg = format_agenda_message(result, max_themes=3)
        assert "Topic 0" in msg
        assert "Topic 2" in msg
        assert "Topic 3" not in msg

    def test_max_items_limit_applied(self):
        """max_items を超えるアクションアイテムが切り捨てられること."""
        items = [_make_item(text=f"TODO: task {i}", source_episode=i) for i in range(10)]
        result = _make_result(items=items)
        msg = format_agenda_message(result, max_items=3)
        assert "task 0" in msg
        assert "task 2" in msg
        assert "task 3" not in msg

    def test_max_prompts_limit_applied(self):
        """max_prompts を超える論点が切り捨てられること."""
        prompts = [_make_prompt(sentence=f"設計方針 {i} はどうすべきか?") for i in range(10)]
        result = _make_result(prompts=prompts)
        msg = format_agenda_message(result, max_prompts=3)
        assert "設計方針 0" in msg
        assert "設計方針 2" in msg
        assert "設計方針 3" not in msg

    def test_long_action_item_truncated(self):
        """80 字を超えるアクションアイテムのテキストが切り捨てられること."""
        long_text = "TODO: " + "あ" * 100
        result = _make_result(items=[_make_item(text=long_text)])
        msg = format_agenda_message(result, max_items=1)
        assert "..." in msg
        assert long_text not in msg

    def test_long_prompt_truncated(self):
        """80 字を超える論点文が切り捨てられること."""
        long_sentence = "このシステムの" + "設計" * 40 + "はどうすべきか?"
        result = _make_result(prompts=[_make_prompt(sentence=long_sentence)])
        msg = format_agenda_message(result)
        assert "..." in msg
        assert long_sentence not in msg

    def test_message_within_length_limit(self):
        """生成されたメッセージが _MAX_MESSAGE_LENGTH 以内に収まること."""
        themes = [_make_theme(topic_id=f"t{i}", display_name=f"Topic {i}") for i in range(5)]
        items = [_make_item(text=f"TODO: {'あ' * 80}", source_episode=i) for i in range(5)]
        prompts = [_make_prompt(sentence=f"{'設計' * 40}?", source_episode=i) for i in range(5)]
        candidates = [_make_news_candidate(title=f"News item {i}" * 5) for i in range(5)]
        result = _make_result(themes=themes, items=items, prompts=prompts)
        msg = format_agenda_message(result, news_candidates=candidates)
        assert len(msg) <= _MAX_MESSAGE_LENGTH

    def test_themes_section_shows_display_name_without_episode_refs(self):
        """recurring_theme のトピック名が表示され、エピソード参照が含まれないこと."""
        theme = _make_theme(display_name="インフラ / Terraform", evidence_episodes=[1, 2])
        result = _make_result(themes=[theme])
        msg = format_agenda_message(result)
        assert "インフラ / Terraform" in msg
        # エピソード参照は themes セクションに表示しない
        assert "(#1" not in msg
        assert "(#2" not in msg

    def test_source_episode_shown_in_action_items(self):
        """action_item にエピソード番号が含まれること."""
        result = _make_result(items=[_make_item(source_episode=3)])
        msg = format_agenda_message(result, max_items=1)
        assert "[#3]" in msg

    def test_source_episode_shown_in_prompts(self):
        """discussion_prompt にエピソード番号が含まれること."""
        result = _make_result(prompts=[_make_prompt(source_episode=5)])
        msg = format_agenda_message(result)
        assert "[#5]" in msg

    def test_section_budget_overflow_skips_section(self):
        """budget を超えるセクションが丸ごとスキップされること."""
        result = _make_result(
            themes=[_make_theme()],
            items=[_make_item()],
            prompts=[_make_prompt()],
        )
        msg = format_agenda_message(result, max_items=0)
        assert "アクションアイテム" not in msg
        assert "最近よく出てきたテーマ" in msg
        assert "気になっている問い" in msg


# ── TestNewsSectionBuilding ────────────────────────────────────────────────────


class TestNewsSectionBuilding:
    """news section の構築テストクラス."""

    def test_news_section_shown_with_candidates(self):
        """news_candidates が渡された場合、ニュースセクションが表示されること."""
        result = _make_result()
        candidates = [_make_news_candidate()]
        msg = format_agenda_message(result, news_candidates=candidates)
        assert "最近の会話と繋がりそうなニュース" in msg

    def test_news_section_omitted_when_none(self):
        """news_candidates=None の場合、ニュースセクションが省略されること."""
        result = _make_result()
        msg = format_agenda_message(result, news_candidates=None)
        assert "最近の会話と繋がりそうなニュース" not in msg

    def test_news_section_omitted_when_empty_list(self):
        """news_candidates=[] の場合、ニュースセクションが省略されること."""
        result = _make_result()
        msg = format_agenda_message(result, news_candidates=[])
        assert "最近の会話と繋がりそうなニュース" not in msg

    def test_news_title_and_source_in_message(self):
        """ニュースのタイトルとソースがメッセージに含まれること."""
        result = _make_result()
        candidate = _make_news_candidate(
            title="Cloud Run gen2 cold start improvements",
            source="Google Cloud Blog",
        )
        msg = format_agenda_message(result, news_candidates=[candidate])
        assert "Cloud Run gen2 cold start improvements" in msg
        assert "Google Cloud Blog" in msg

    def test_news_topic_connection_in_message(self):
        """ニュースのトピック接続先 (↳ {topic}) がメッセージに含まれること."""
        result = _make_result()
        candidate = _make_news_candidate(topic_display_name="インフラ / Terraform")
        msg = format_agenda_message(result, news_candidates=[candidate])
        assert "インフラ / Terraform" in msg
        assert "↳" in msg

    def test_max_news_limit_applied(self):
        """max_news を超えるニュース候補が切り捨てられること."""
        result = _make_result()
        candidates = [_make_news_candidate(title=f"News {i}", url=f"https://example.com/{i}") for i in range(10)]
        msg = format_agenda_message(result, news_candidates=candidates, max_news=2)
        assert "News 0" in msg
        assert "News 1" in msg
        assert "News 2" not in msg

    def test_long_news_title_truncated(self):
        """80 字を超えるニュースタイトルが切り捨てられること."""
        long_title = "A" * 100
        result = _make_result()
        candidate = _make_news_candidate(title=long_title)
        msg = format_agenda_message(result, news_candidates=[candidate])
        assert "..." in msg
        assert long_title not in msg

    def test_message_with_news_within_length_limit(self):
        """ニュースセクションを含むメッセージが _MAX_MESSAGE_LENGTH 以内に収まること."""
        themes = [_make_theme(topic_id=f"t{i}", display_name=f"Topic {i}") for i in range(3)]
        prompts = [_make_prompt(sentence=f"設計方針 {i} はどうすべきか?") for i in range(3)]
        candidates = [
            _make_news_candidate(title=f"News article {i}" * 3, url=f"https://example.com/{i}") for i in range(3)
        ]
        result = _make_result(themes=themes, prompts=prompts)
        msg = format_agenda_message(result, news_candidates=candidates)
        assert len(msg) <= _MAX_MESSAGE_LENGTH


# ── TestFormatEpisodeRefs ──────────────────────────────────────────────────────


class TestFormatEpisodeRefs:
    """_format_episode_refs() のテストクラス."""

    def test_single_episode(self):
        """evidence が 1 件のとき (#N) 形式で返ること."""
        evidence = [MentionEvidence(source_episode=1, text="mention", sentence_index=0)]
        assert _format_episode_refs(evidence) == "(#1)"

    def test_multiple_episodes(self):
        """evidence が複数エピソードのとき (#N, #M) 形式で返ること."""
        evidence = [
            MentionEvidence(source_episode=1, text="m1", sentence_index=0),
            MentionEvidence(source_episode=2, text="m2", sentence_index=0),
        ]
        assert _format_episode_refs(evidence) == "(#1, #2)"

    def test_duplicate_episodes_deduplicated(self):
        """同一エピソードの evidence が重複排除されること."""
        evidence = [
            MentionEvidence(source_episode=1, text="m1", sentence_index=0),
            MentionEvidence(source_episode=1, text="m2", sentence_index=1),
            MentionEvidence(source_episode=2, text="m3", sentence_index=0),
        ]
        assert _format_episode_refs(evidence) == "(#1, #2)"

    def test_empty_evidence_returns_empty_string(self):
        """evidence が空リストのとき空文字列を返すこと."""
        assert _format_episode_refs([]) == ""


# ── TestTruncate ───────────────────────────────────────────────────────────────


class TestTruncate:
    """_truncate() のテストクラス."""

    def test_short_text_unchanged(self):
        """max_len 以内のテキストはそのまま返ること."""
        assert _truncate("abc", 10) == "abc"

    def test_exact_length_unchanged(self):
        """ちょうど max_len のテキストはそのまま返ること."""
        assert _truncate("a" * 10, 10) == "a" * 10

    def test_long_text_truncated_with_ellipsis(self):
        """max_len を超えるテキストが '...' 付きで切り詰められること."""
        result = _truncate("a" * 20, 10)
        assert result.endswith("...")
        assert len(result) == 10

    def test_truncated_length_equals_max_len(self):
        """切り詰め後の長さが max_len と等しいこと."""
        result = _truncate("x" * 100, 15)
        assert len(result) == 15


# ── TestBuildAiNewsSection ─────────────────────────────────────────────────────


class TestBuildAiNewsSection:
    """_build_ai_news_section() のユニットテスト."""

    def test_returns_section_with_header(self):
        """返り値に AI ニュースセクションのヘッダーが含まれること."""
        section = _build_ai_news_section("ニュース内容", budget=1000)
        assert "今週の会話の続きになりそうな話題" in section

    def test_returns_section_with_body_text(self):
        """返り値に渡したテキストが含まれること."""
        section = _build_ai_news_section("テスト本文テキスト", budget=1000)
        assert "テスト本文テキスト" in section

    def test_empty_string_returns_none(self):
        """空文字列の場合 None を返すこと."""
        assert _build_ai_news_section("", budget=1000) is None

    def test_whitespace_only_returns_none(self):
        """空白のみの場合 None を返すこと."""
        assert _build_ai_news_section("   \n\t  ", budget=1000) is None

    def test_truncates_to_max_ai_section_length(self):
        """テキストが _MAX_AI_NEWS_SECTION_LENGTH を超える場合に切り詰めること."""
        long_text = "a" * (_MAX_AI_NEWS_SECTION_LENGTH + 200)
        section = _build_ai_news_section(long_text, budget=_MAX_AI_NEWS_SECTION_LENGTH + 500)
        # body 部分が _MAX_AI_NEWS_SECTION_LENGTH 以内に収まること
        assert section is not None
        # ヘッダー + body の合計がハード上限を超えないこと
        assert len(section) <= _MAX_AI_NEWS_SECTION_LENGTH + 50  # header margin

    def test_truncates_to_budget_when_smaller_than_max(self):
        """budget が _MAX_AI_NEWS_SECTION_LENGTH より小さい場合は budget で切り詰めること."""
        text = "b" * 500
        section = _build_ai_news_section(text, budget=100)
        # header + body が budget に収まること
        assert section is not None
        assert len(section) <= 100 + len("🔍 **今週の会話の続きになりそうな話題**\n\n")

    def test_returns_none_when_budget_too_small(self):
        """budget が極端に小さい場合 None を返すこと."""
        # budget - 2 (separator) <= 0 のケース
        assert _build_ai_news_section("text", budget=1) is None

    def test_short_text_not_truncated(self):
        """budget に余裕がある場合、短いテキストはそのまま返ること."""
        text = "短いニュース本文"
        section = _build_ai_news_section(text, budget=1000)
        assert text in section
        assert "..." not in section


# ── TestAiNewsSectionInFormatter ──────────────────────────────────────────────


class TestAiNewsSectionInFormatter:
    """format_agenda_message() の ai_news_section パスのテスト."""

    def test_ai_news_section_shown_in_message(self):
        """ai_news_section が渡された場合、その内容がメッセージに含まれること."""
        result = _make_result()
        msg = format_agenda_message(result, ai_news_section="**テストニュース**\n会話の種: 面白い視点")
        assert "テストニュース" in msg
        assert "会話の種" in msg

    def test_ai_section_header_shown(self):
        """ai_news_section が渡された場合、AI ニュースヘッダーが含まれること."""
        result = _make_result()
        msg = format_agenda_message(result, ai_news_section="ニュース内容")
        assert "今週の会話の続きになりそうな話題" in msg

    def test_ai_section_takes_priority_over_news_candidates(self):
        """ai_news_section が優先され、news_candidates の RSS セクションが表示されないこと."""
        result = _make_result()
        candidates = [_make_news_candidate(title="RSS Article")]
        msg = format_agenda_message(
            result,
            ai_news_section="AI generated content",
            news_candidates=candidates,
        )
        assert "今週の会話の続きになりそうな話題" in msg
        assert "最近の会話と繋がりそうなニュース" not in msg
        assert "RSS Article" not in msg

    def test_footer_shows_ai_research_when_ai_section_given(self):
        """ai_news_section が渡された場合、フッターに 'AI リサーチ' が含まれること."""
        result = _make_result(analyzed_episodes=5)
        msg = format_agenda_message(result, ai_news_section="ニュース内容")
        assert "AI リサーチ" in msg
        assert "5 エピソード" in msg

    def test_footer_does_not_show_ai_research_when_none(self):
        """ai_news_section=None の場合、フッターに 'AI リサーチ' が含まれないこと."""
        result = _make_result()
        msg = format_agenda_message(result)
        assert "AI リサーチ" not in msg

    def test_none_ai_section_falls_back_to_news_candidates(self):
        """ai_news_section=None の場合、news_candidates の RSS セクションが使われること (後方互換)."""
        result = _make_result()
        candidates = [_make_news_candidate(title="RSS Fallback Article")]
        msg = format_agenda_message(result, ai_news_section=None, news_candidates=candidates)
        assert "最近の会話と繋がりそうなニュース" in msg
        assert "RSS Fallback Article" in msg

    def test_empty_ai_section_falls_back_to_news_candidates(self):
        """ai_news_section が空文字列の場合、news_candidates が使われること."""
        result = _make_result()
        candidates = [_make_news_candidate(title="RSS Fallback Article")]
        # 空文字列の ai_news_section は _build_ai_news_section が None を返す
        # → フォーマッタは news_candidates を使う
        msg = format_agenda_message(result, ai_news_section="", news_candidates=candidates)
        assert "RSS Fallback Article" in msg

    def test_message_with_ai_section_within_length_limit(self):
        """ai_news_section を含むメッセージが _MAX_MESSAGE_LENGTH 以内に収まること."""
        themes = [_make_theme(topic_id=f"t{i}", display_name=f"Topic {i}") for i in range(3)]
        prompts = [_make_prompt(sentence=f"設計方針 {i} はどうすべきか?") for i in range(3)]
        long_ai_section = "AI ニュース内容。" * 200  # 意図的に長い
        result = _make_result(themes=themes, prompts=prompts)
        msg = format_agenda_message(result, ai_news_section=long_ai_section)
        assert len(msg) <= _MAX_MESSAGE_LENGTH

    def test_themes_and_ai_section_coexist(self):
        """テーマセクションと AI ニュースセクションが共存できること."""
        themes = [_make_theme(display_name="インフラ / Terraform")]
        result = _make_result(themes=themes)
        msg = format_agenda_message(result, ai_news_section="最新インフラ動向")
        assert "最近よく出てきたテーマ" in msg
        assert "今週の会話の続きになりそうな話題" in msg
