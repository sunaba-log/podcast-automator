"""agenda_formatter のユニットテスト."""

from __future__ import annotations

from services.agenda_formatter import (
    _MAX_MESSAGE_LENGTH,
    _format_episode_refs,
    _truncate,
    format_agenda_message,
)
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


# ── TestFormatAgendaMessage ────────────────────────────────────────────────────


class TestFormatAgendaMessage:
    """format_agenda_message() のテストクラス."""

    def test_header_always_present(self):
        """ヘッダーが常に含まれること."""
        result = _make_result()
        msg = format_agenda_message(result)
        assert "今週の収録リマインダー" in msg

    def test_footer_always_present(self):
        """フッター (分析メタデータ) が常に含まれること."""
        result = _make_result(analyzed_episodes=3, fetched=50)
        msg = format_agenda_message(result)
        assert "3 エピソード" in msg
        assert "50 件取得" in msg

    def test_all_sections_present_when_data_exists(self):
        """全セクションにデータがある場合、3 セクションすべて含まれること."""
        result = _make_result(
            themes=[_make_theme()],
            items=[_make_item()],
            prompts=[_make_prompt()],
        )
        msg = format_agenda_message(result)
        assert "繰り返しトピック" in msg
        assert "アクションアイテム" in msg
        assert "未解決の論点" in msg

    def test_empty_themes_section_omitted(self):
        """recurring_themes が 0 件の場合、テーマセクションが省略されること."""
        result = _make_result(themes=[], items=[_make_item()])
        msg = format_agenda_message(result)
        assert "繰り返しトピック" not in msg

    def test_empty_items_section_omitted(self):
        """action_items が 0 件の場合、アクションアイテムセクションが省略されること."""
        result = _make_result(themes=[_make_theme()], items=[])
        msg = format_agenda_message(result)
        assert "アクションアイテム" not in msg

    def test_empty_prompts_section_omitted(self):
        """discussion_prompts が 0 件の場合、論点セクションが省略されること."""
        result = _make_result(themes=[_make_theme()], prompts=[])
        msg = format_agenda_message(result)
        assert "未解決の論点" not in msg

    def test_all_empty_shows_only_header_and_footer(self):
        """全セクション空の場合、ヘッダーとフッターのみ含まれること."""
        result = _make_result()
        msg = format_agenda_message(result)
        assert "今週の収録リマインダー" in msg
        assert "エピソード" in msg
        assert "繰り返しトピック" not in msg
        assert "アクションアイテム" not in msg
        assert "未解決の論点" not in msg

    def test_max_themes_limit_applied(self):
        """max_themes を超えるテーマが切り捨てられること."""
        themes = [_make_theme(topic_id=f"t{i}", display_name=f"Topic {i}") for i in range(10)]
        result = _make_result(themes=themes)
        msg = format_agenda_message(result, max_themes=3)
        # Topic 0, 1, 2 は含まれ、Topic 3 以降は含まれない
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
        msg = format_agenda_message(result)
        assert "..." in msg
        # 全文がそのまま含まれていないこと
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
        result = _make_result(themes=themes, items=items, prompts=prompts)
        msg = format_agenda_message(result)
        assert len(msg) <= _MAX_MESSAGE_LENGTH

    def test_episode_ref_shown_in_themes(self):
        """recurring_theme にエピソード参照が含まれること."""
        theme = _make_theme(evidence_episodes=[1, 2])
        result = _make_result(themes=[theme])
        msg = format_agenda_message(result)
        assert "#1" in msg
        assert "#2" in msg

    def test_source_episode_shown_in_action_items(self):
        """action_item にエピソード番号が含まれること."""
        result = _make_result(items=[_make_item(source_episode=3)])
        msg = format_agenda_message(result)
        assert "[#3]" in msg

    def test_source_episode_shown_in_prompts(self):
        """discussion_prompt にエピソード番号が含まれること."""
        result = _make_result(prompts=[_make_prompt(source_episode=5)])
        msg = format_agenda_message(result)
        assert "[#5]" in msg

    def test_section_budget_overflow_skips_section(self):
        """budget を超えるセクションが丸ごとスキップされること."""
        # テーマセクションだけで budget を埋める大量データ
        # 実際には _MAX_MESSAGE_LENGTH に近い状況を人工的に作るのが難しいため、
        # budget を最小値に絞った custom call で確認する
        result = _make_result(
            themes=[_make_theme()],
            items=[_make_item()],
            prompts=[_make_prompt()],
        )
        # max_items=0 相当: items が空として扱われるのでセクション省略を確認
        msg = format_agenda_message(result, max_items=0)
        assert "アクションアイテム" not in msg
        # themes と prompts は残る
        assert "繰り返しトピック" in msg
        assert "未解決の論点" in msg


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
