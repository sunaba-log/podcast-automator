"""TranscriptAnalyzer のユニットテスト."""

import json

import pytest

from infrastructure.discord_fetcher import DiscordMessage
from services.transcript_analyzer import Episode, PromptType, SortPolicy, TranscriptAnalyzer, TranscriptBoundaryError


def _msg(
    *,
    msg_id: str,
    content: str,
    timestamp: str,
    author_name: str = "bot",
) -> DiscordMessage:
    """テスト用 DiscordMessage ファクトリ."""
    return DiscordMessage(
        id=msg_id,
        content=content,
        timestamp=timestamp,
        author_name=author_name,
    )


def _episode(number: int) -> Episode:
    """テスト用 Episode ファクトリ."""
    return Episode(
        number=number,
        content=f"Content of episode {number}",
        timestamp=f"2024-01-{number:02d}T00:00:00Z",
        source_message_ids=[str(number)],
    )


class TestReconstructEpisodes:
    """reconstruct_episodes() のテストクラス."""

    def test_single_episode_single_message(self):
        """単一境界メッセージから Episode が 1 件生成されること."""
        analyzer = TranscriptAnalyzer()
        messages = [
            _msg(msg_id="1", content="#42 Meeting Transcript:\nHello world", timestamp="2024-01-01T00:00:00Z"),
        ]
        episodes, warnings = analyzer.reconstruct_episodes(messages)

        assert len(episodes) == 1
        assert episodes[0].number == 42
        assert "Hello world" in episodes[0].content
        assert episodes[0].source_message_ids == ["1"]
        assert warnings == []

    def test_single_episode_split_across_multiple_messages(self):
        """split_message による複数メッセージが 1 Episode に結合されること."""
        analyzer = TranscriptAnalyzer()
        messages = [
            _msg(msg_id="1", content="#1 Meeting Transcript:\nPart A", timestamp="2024-01-01T00:00:00Z"),
            _msg(msg_id="2", content="Part B", timestamp="2024-01-01T00:01:00Z"),
            _msg(msg_id="3", content="Part C", timestamp="2024-01-01T00:02:00Z"),
        ]
        episodes, warnings = analyzer.reconstruct_episodes(messages)

        assert len(episodes) == 1
        assert "Part A" in episodes[0].content
        assert "Part B" in episodes[0].content
        assert "Part C" in episodes[0].content
        assert episodes[0].source_message_ids == ["1", "2", "3"]
        assert warnings == []

    def test_multiple_episodes_reconstructed_in_order(self):
        """複数の境界メッセージから複数 Episode が古い順に生成されること."""
        analyzer = TranscriptAnalyzer()
        messages = [
            _msg(msg_id="1", content="#1 Meeting Transcript:\nEp1", timestamp="2024-01-01T00:00:00Z"),
            _msg(msg_id="2", content="#2 Meeting Transcript:\nEp2", timestamp="2024-01-08T00:00:00Z"),
            _msg(msg_id="3", content="#3 Meeting Transcript:\nEp3", timestamp="2024-01-15T00:00:00Z"),
        ]
        episodes, warnings = analyzer.reconstruct_episodes(messages)

        assert len(episodes) == 3
        assert [ep.number for ep in episodes] == [1, 2, 3]
        assert warnings == []

    def test_empty_messages_returns_empty_episodes(self):
        """空のメッセージリストから空の Episode リストが返されること."""
        analyzer = TranscriptAnalyzer()
        episodes, warnings = analyzer.reconstruct_episodes([])

        assert episodes == []
        assert warnings == []

    def test_orphan_message_before_boundary_generates_warning(self):
        """境界確立前の孤立メッセージが警告に収集され、後続 Episode は正常に生成されること."""
        analyzer = TranscriptAnalyzer()
        messages = [
            _msg(msg_id="0", content="random chat before any episode", timestamp="2024-01-01T00:00:00Z"),
            _msg(msg_id="1", content="#1 Meeting Transcript:\nContent", timestamp="2024-01-01T00:01:00Z"),
        ]
        episodes, warnings = analyzer.reconstruct_episodes(messages)

        assert len(episodes) == 1
        assert len(warnings) == 1
        assert "orphan" in warnings[0]
        assert "0" in warnings[0]  # offending message id

    def test_episode_number_regression_generates_warning_in_non_strict_mode(self):
        """エピソード番号の逆転が strict=False で警告に収集されること."""
        analyzer = TranscriptAnalyzer()
        messages = [
            _msg(msg_id="1", content="#5 Meeting Transcript:\nEp5", timestamp="2024-01-01T00:00:00Z"),
            _msg(msg_id="2", content="#3 Meeting Transcript:\nEp3", timestamp="2024-01-08T00:00:00Z"),
        ]
        _episodes, warnings = analyzer.reconstruct_episodes(messages, strict=False)

        assert len(warnings) == 1
        assert "regression" in warnings[0].lower()

    def test_episode_number_regression_raises_in_strict_mode(self):
        """エピソード番号の逆転が strict=True で TranscriptBoundaryError を raise すること."""
        analyzer = TranscriptAnalyzer()
        messages = [
            _msg(msg_id="1", content="#5 Meeting Transcript:\nEp5", timestamp="2024-01-01T00:00:00Z"),
            _msg(msg_id="2", content="#3 Meeting Transcript:\nEp3", timestamp="2024-01-08T00:00:00Z"),
        ]
        with pytest.raises(TranscriptBoundaryError) as exc_info:
            analyzer.reconstruct_episodes(messages, strict=True)

        assert exc_info.value.offending_message_id == "2"

    def test_unexpected_author_in_continuation_generates_warning(self):
        """continuation メッセージの author が境界メッセージと異なる場合に警告が出ること."""
        analyzer = TranscriptAnalyzer()
        messages = [
            _msg(
                msg_id="1",
                content="#1 Meeting Transcript:\nContent",
                timestamp="2024-01-01T00:00:00Z",
                author_name="bot",
            ),
            _msg(msg_id="2", content="continuation", timestamp="2024-01-01T00:01:00Z", author_name="someone_else"),
        ]
        _episodes, warnings = analyzer.reconstruct_episodes(messages)

        assert len(warnings) == 1
        assert "Unexpected author" in warnings[0]
        assert "someone_else" in warnings[0]

    def test_timestamp_sort_applied_regardless_of_input_order(self):
        """入力メッセージが新しい順でも timestamp 昇順にソートされて Episode が構築されること."""
        analyzer = TranscriptAnalyzer()
        # Discord API は新しい順で返すが、正しく処理できること
        messages = [
            _msg(msg_id="2", content="#2 Meeting Transcript:\nEp2", timestamp="2024-01-08T00:00:00Z"),
            _msg(msg_id="1", content="#1 Meeting Transcript:\nEp1", timestamp="2024-01-01T00:00:00Z"),
        ]
        episodes, warnings = analyzer.reconstruct_episodes(messages)

        assert [ep.number for ep in episodes] == [1, 2]
        assert warnings == []


class TestBuildAgenda:
    """build_agenda() のテストクラス."""

    def test_metadata_fields_correctly_populated(self):
        """AgendaMetadata の各フィールドが正しく設定されること."""
        analyzer = TranscriptAnalyzer()
        episodes = [_episode(n) for n in [1, 2, 3]]

        result = analyzer.build_agenda(
            episodes=episodes,
            recurring_themes=[],
            action_items=[],
            discussion_prompts=[],
            generated_at="2024-01-15T00:00:00+00:00",
            analysis_window_size=50,
            fetched_message_count=42,
        )

        assert result.metadata.generated_at == "2024-01-15T00:00:00+00:00"
        assert result.metadata.analysis_window_size == 50
        assert result.metadata.fetched_message_count == 42
        # source_episode_numbers は降順
        assert result.metadata.source_episode_numbers == [3, 2, 1]
        assert result.metadata.sort_policy == str(SortPolicy.continuity)

    def test_empty_episodes_returns_valid_agenda_result(self):
        """エピソードが 0 件でも AgendaResult が正常に生成されること."""
        analyzer = TranscriptAnalyzer()

        result = analyzer.build_agenda(
            episodes=[],
            recurring_themes=[],
            action_items=[],
            discussion_prompts=[],
            generated_at="2024-01-15T00:00:00+00:00",
            analysis_window_size=50,
            fetched_message_count=0,
        )

        assert result.analyzed_episodes == 0
        assert result.metadata.source_episode_numbers == []
        assert result.recurring_themes == []
        assert result.action_items == []
        assert result.discussion_prompts == []

    def test_hybrid_sort_policy_raises_not_implemented(self):
        """sort_policy=hybrid が NotImplementedError を raise すること."""
        analyzer = TranscriptAnalyzer()

        with pytest.raises(NotImplementedError):
            analyzer.build_agenda(
                episodes=[],
                recurring_themes=[],
                action_items=[],
                discussion_prompts=[],
                sort_policy=SortPolicy.hybrid,
                generated_at="2024-01-15T00:00:00+00:00",
                analysis_window_size=50,
                fetched_message_count=0,
            )

    def test_to_dict_is_json_serializable(self):
        """AgendaResult.to_dict() が json.dumps() 可能な dict を返すこと."""
        analyzer = TranscriptAnalyzer()
        episodes = [_episode(1)]

        result = analyzer.build_agenda(
            episodes=episodes,
            recurring_themes=[],
            action_items=[],
            discussion_prompts=[],
            generated_at="2024-01-15T00:00:00+00:00",
            analysis_window_size=50,
            fetched_message_count=5,
        )

        d = result.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        assert isinstance(json_str, str)
        assert "schema_version" in json_str
        assert "1.0" in json_str
        assert "generated_at" in json_str


# ── Phase 1-B test data ────────────────────────────────────────────────────────

# realistic transcript-style content (2 episodes)
_EP1_CONTENT = """\
#1 Meeting Transcript:
今週は Terraform の構成を見直した。GCP の Cloud Run に新しい Job を追加した。
インフラのデプロイフローを改善したい。
TODO: Cloud Scheduler の設定を確認する
Discord の Webhook URL を Secret Manager で管理する方針で進める。
将来的には自動化をもっと強化したい。
このアーキテクチャ設計はどう実装すべきか?
"""

_EP2_CONTENT = """\
#2 Meeting Transcript:
前回の Terraform apply の失敗を調査中。fix が必要。
Discord Bot の設定を確認する必要があり、確認が必要なことが多い。
AI / LLM を活用したアジェンダ生成を今後進めたい。
設計方針はまだ決まっていないため検討中。
アーキテクチャの方針はどうすべきか?
GCP の Cloud Run と Cloud Scheduler の連携を実装する予定。
"""


def _make_episodes_from_content(*contents: str) -> list[Episode]:
    """テスト用 Episode リストをコンテンツ文字列から生成するファクトリ."""
    analyzer = TranscriptAnalyzer()
    messages = [
        DiscordMessage(
            id=str(i + 1),
            content=content,
            timestamp=f"2024-01-{i + 1:02d}T00:00:00Z",
            author_name="bot",
        )
        for i, content in enumerate(contents)
    ]
    episodes, _ = analyzer.reconstruct_episodes(messages)
    return episodes


class TestExtractRecurringThemes:
    """extract_recurring_themes() のテストクラス."""

    def test_detects_terraform_keyword(self):
        """'Terraform' キーワードが infra-terraform トピックにマッチすること."""
        episodes = _make_episodes_from_content(_EP1_CONTENT)
        analyzer = TranscriptAnalyzer()

        themes = analyzer.extract_recurring_themes(episodes)

        topic_ids = [t.topic_id for t in themes]
        assert "infra-terraform" in topic_ids

    def test_episode_count_increases_across_episodes(self):
        """同じトピックが複数エピソードで言及された場合 episode_count が増えること."""
        episodes = _make_episodes_from_content(_EP1_CONTENT, _EP2_CONTENT)
        analyzer = TranscriptAnalyzer()

        themes = analyzer.extract_recurring_themes(episodes)
        terraform_theme = next(t for t in themes if t.topic_id == "infra-terraform")

        # Terraform が両エピソードに登場する
        assert terraform_theme.episode_count == 2

    def test_evidence_capped_at_3(self):
        """evidence は最大 3 件に制限されること."""
        # Terraform が多数登場するコンテンツ
        heavy_content = "#99 Meeting Transcript:\n" + "\n".join(
            [f"Terraform の設定 {i} を確認した。GCP に deploy した。" for i in range(10)]
        )
        episodes = _make_episodes_from_content(heavy_content)
        analyzer = TranscriptAnalyzer()

        themes = analyzer.extract_recurring_themes(episodes)
        terraform_theme = next(t for t in themes if t.topic_id == "infra-terraform")

        assert len(terraform_theme.evidence) <= 3

    def test_score_equals_mention_count(self):
        """score が mention_count と等しいこと (Phase 1-B: simple count)."""
        episodes = _make_episodes_from_content(_EP1_CONTENT)
        analyzer = TranscriptAnalyzer()

        themes = analyzer.extract_recurring_themes(episodes)
        for theme in themes:
            assert theme.score == float(theme.mention_count)

    def test_no_match_topic_not_returned(self):
        """キーワードが 1 件もマッチしないトピックは結果に含まれないこと."""
        # Terraform のみに言及し、ポッドキャスト収録には一切言及しない
        content = "#1 Meeting Transcript:\nTerraform の設定を見直した。GCP に deploy した。"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        themes = analyzer.extract_recurring_themes(episodes)
        topic_ids = [t.topic_id for t in themes]

        assert "product-podcast" not in topic_ids

    def test_results_sorted_by_mention_count_desc(self):
        """結果が mention_count 降順にソートされていること."""
        episodes = _make_episodes_from_content(_EP1_CONTENT, _EP2_CONTENT)
        analyzer = TranscriptAnalyzer()

        themes = analyzer.extract_recurring_themes(episodes)
        counts = [t.mention_count for t in themes]

        assert counts == sorted(counts, reverse=True)


class TestExtractActionItems:
    """extract_action_items() のテストクラス."""

    def test_detects_todo_keyword(self):
        """'TODO' を含む行がアクションアイテムとして抽出されること."""
        episodes = _make_episodes_from_content(_EP1_CONTENT)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert any("TODO" in item.text for item in items)

    def test_detects_fix_keyword_lowercase(self):
        """'fix' (小文字) を含む行がアクションアイテムとして抽出されること."""
        episodes = _make_episodes_from_content(_EP2_CONTENT)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert any("fix" in item.text for item in items)

    def test_detects_fix_keyword_case_insensitive(self):
        """'Fix' / 'FIX' など大文字混じりでも抽出されること (case-insensitive)."""
        content = "#1 Meeting Transcript:\nFix: API のレスポンスが遅い件を対処する。\nFIX the deploy script."
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert len(items) == 2

    def test_detects_investigate_case_insensitive(self):
        """'Investigate' / 'INVESTIGATE' でも抽出されること."""
        content = "#1 Meeting Transcript:\nInvestigate: Cloud Run のコールドスタートを調査する。"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert len(items) == 1
        assert "Investigate" in items[0].text

    def test_detects_japanese_keyword(self):
        """'確認する' を含む行がアクションアイテムとして抽出されること."""
        episodes = _make_episodes_from_content(_EP1_CONTENT)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert any("確認する" in item.text for item in items)

    def test_source_episode_number_correct(self):
        """抽出されたアクションアイテムの source_episode が正しいこと."""
        episodes = _make_episodes_from_content(_EP1_CONTENT, _EP2_CONTENT)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        # source_episode が有効なエピソード番号の範囲内
        episode_numbers = {ep.number for ep in episodes}
        for item in items:
            assert item.source_episode in episode_numbers

    def test_plain_text_line_not_extracted(self):
        """明示的なキーワードを含まない通常の行は抽出されないこと."""
        content = "#1 Meeting Transcript:\n今日はいい天気だった。昨日のことを話した。"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert items == []


class TestExtractDiscussionPrompts:
    """extract_discussion_prompts() のテストクラス."""

    def test_detects_design_decision_bekika(self):
        """'べきか' を含む文が design_decision に分類されること."""
        content = "#1 Meeting Transcript:\nこのアーキテクチャはどう実装すべきか?"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert any(p.prompt_type == PromptType.design_decision for p in prompts)

    def test_detects_future_consideration_kongo(self):
        """'今後' を含む文が future_consideration に分類されること."""
        content = "#1 Meeting Transcript:\nAI / LLM を活用したアジェンダ生成を今後進めたい。"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert any(p.prompt_type == PromptType.future_consideration for p in prompts)

    def test_detects_uncertain_kentouchu(self):
        """'検討中' を含む文が uncertain に分類されること."""
        # design_decision キーワードを含まない純粋な uncertain 文
        content = "#1 Meeting Transcript:\n詳細はまだ検討中です。"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert any(p.prompt_type == PromptType.uncertain for p in prompts)

    def test_design_decision_takes_priority_over_question(self):
        """design_decision が question より優先されること (PROMPT_PATTERNS の順序)."""
        # "べきか" で終わる文は ASCII ? も含む場合でも design_decision
        content = "#1 Meeting Transcript:\nどう設計すべきか?"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        types = [p.prompt_type for p in prompts]
        assert PromptType.design_decision in types
        # question に分類されていないこと (design_decision が先に評価されるため)
        assert PromptType.question not in types

    def test_no_keyword_line_not_extracted(self):
        """どのパターンにもマッチしない行は抽出されないこと."""
        content = "#1 Meeting Transcript:\n今週の収録が完了した。音声ファイルをアップロードした。"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert prompts == []


class TestIsNoiseLine:
    """_is_noise_line() ヘルパーのテストクラス."""

    def test_short_line_is_noise(self):
        """7 文字未満の行がノイズ判定されること."""
        analyzer = TranscriptAnalyzer()
        assert analyzer._is_noise_line("fix") is True  # 3 chars
        assert analyzer._is_noise_line("URL:") is True  # 4 chars
        assert analyzer._is_noise_line("abc") is True  # 3 chars

    def test_description_prefix_is_noise(self):
        """'Description:' で始まる行がノイズ判定されること."""
        analyzer = TranscriptAnalyzer()
        assert analyzer._is_noise_line("Description: <p>今後の方針を検討する</p>") is True
        assert analyzer._is_noise_line("Description:<p>text</p>") is True

    def test_title_prefix_is_noise(self):
        """'Title:' で始まる行がノイズ判定されること."""
        analyzer = TranscriptAnalyzer()
        assert analyzer._is_noise_line("Title: Episode #22 - 設計回") is True

    def test_url_prefix_is_noise(self):
        """'URL:' で始まる行がノイズ判定されること."""
        analyzer = TranscriptAnalyzer()
        assert analyzer._is_noise_line("URL: https://example.com/episode/42") is True

    def test_https_standalone_is_noise(self):
        """'https://' で始まる行がノイズ判定されること."""
        analyzer = TranscriptAnalyzer()
        assert analyzer._is_noise_line("https://example.com/episode/42?utm_source=rss") is True

    def test_new_podcast_processed_is_noise(self):
        """'New Podcast Processed' で始まる行がノイズ判定されること."""
        analyzer = TranscriptAnalyzer()
        assert analyzer._is_noise_line("New Podcast Processed") is True

    def test_normal_long_sentence_is_not_noise(self):
        """通常の議論行(7 文字以上・metadata なし)がノイズ判定されないこと."""
        analyzer = TranscriptAnalyzer()
        assert analyzer._is_noise_line("このアーキテクチャはどう実装すべきか?") is False
        assert analyzer._is_noise_line("Terraform の設定を見直した。") is False

    def test_9char_sentence_is_not_noise(self):
        """9 文字の文(7 文字閾値の境界値)がノイズ判定されないこと."""
        analyzer = TranscriptAnalyzer()
        # "どう設計すべきか?" = 9 chars — 既存テストの sentinel 値
        assert analyzer._is_noise_line("どう設計すべきか?") is False


class TestActionItemWordBoundary:
    """action item の word-boundary マッチングのテストクラス."""

    def test_fix_does_not_match_prefix(self):
        """'prefix' に 'fix' の word-boundary マッチが発生しないこと."""
        content = "#1 Meeting Transcript:\nprefixをコンポーネントに設定する。これは prefix 方式で動作する。"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert items == []

    def test_fix_does_not_match_fixing(self):
        """'fixing' に 'fix' の word-boundary マッチが発生しないこと."""
        content = "#1 Meeting Transcript:\nWe are fixing the deploy pipeline issues."
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert items == []

    def test_fix_matches_standalone_word(self):
        """'fix' が単語として現れた場合にアクションアイテムとして抽出されること."""
        content = "#1 Meeting Transcript:\nfix: the deploy script before next release."
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert len(items) == 1

    def test_fix_matches_with_colon(self):
        """'Fix:' 形式でもアクションアイテムとして抽出されること."""
        content = "#1 Meeting Transcript:\nFix: API のレスポンス遅延を修正する。"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert len(items) == 1

    def test_investigate_does_not_match_reinvestigate(self):
        """'reinvestigate' に 'investigate' の word-boundary マッチが発生しないこと."""
        content = "#1 Meeting Transcript:\nWe may need to reinvestigate the root cause later."
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert items == []

    def test_todo_matches_with_colon(self):
        """'TODO:' 形式でもアクションアイテムとして抽出されること."""
        content = "#1 Meeting Transcript:\nTODO: Cloud Scheduler の設定を確認する"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert len(items) == 1


class TestActionItemMarkdownStrip:
    """ActionItem.text の markdown marker strip のテストクラス."""

    def test_bullet_asterisk_stripped(self):
        """'* keyword' の leading '* ' が ActionItem.text から除去されること."""
        content = "#1 Meeting Transcript:\n* TODO: Cloud Scheduler の設定を確認する"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert len(items) == 1
        assert not items[0].text.startswith("*")
        assert "TODO" in items[0].text

    def test_bullet_dash_stripped(self):
        """'- keyword' の leading '- ' が ActionItem.text から除去されること."""
        content = "#1 Meeting Transcript:\n- 対応する: Webhook URL を更新する"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert len(items) == 1
        assert not items[0].text.startswith("-")

    def test_blockquote_marker_stripped(self):
        """'> keyword' の leading '> ' が ActionItem.text から除去されること."""
        content = "#1 Meeting Transcript:\n> 確認する: GCP の billing を見直す"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert len(items) == 1
        assert not items[0].text.startswith(">")

    def test_no_marker_line_text_unchanged(self):
        """markdown marker のない行は変更されないこと."""
        content = "#1 Meeting Transcript:\nTODO: Cloud Scheduler の設定を確認する"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert len(items) == 1
        assert items[0].text.startswith("TODO:")


class TestExtractorNoiseFiltering:
    """metadata ノイズが action_items / discussion_prompts から除外されること."""

    def test_description_html_excluded_from_action_items(self):
        """'Description: <p>...' 行が action_items に含まれないこと."""
        content = "#1 Meeting Transcript:\nDescription: <p>今後の方針を検討する必要があります</p>"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert items == []

    def test_description_html_excluded_from_prompts(self):
        """'Description: <p>...' 行が discussion_prompts に含まれないこと."""
        content = "#1 Meeting Transcript:\nDescription: <p>今後の方針を検討する必要があります</p>"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert prompts == []

    def test_url_line_excluded_from_action_items(self):
        """'URL:' 行が action_items に含まれないこと."""
        content = "#1 Meeting Transcript:\nURL: https://example.com/episode/42"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert items == []

    def test_url_line_excluded_from_prompts(self):
        """'URL:' 行が discussion_prompts に含まれないこと."""
        content = "#1 Meeting Transcript:\nURL: https://example.com/episode/42"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert prompts == []

    def test_standalone_https_excluded_from_prompts(self):
        """'https://...' 行が discussion_prompts に含まれないこと."""
        content = "#1 Meeting Transcript:\nhttps://podcast.example.com/ep/42?utm_source=rss"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert prompts == []

    def test_new_podcast_processed_excluded_from_prompts(self):
        """'New Podcast Processed' 行が discussion_prompts に含まれないこと."""
        content = "#1 Meeting Transcript:\nNew Podcast Processed"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert prompts == []

    def test_new_podcast_processed_excluded_from_action_items(self):
        """'New Podcast Processed' 行が action_items に含まれないこと."""
        content = "#1 Meeting Transcript:\nNew Podcast Processed"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)

        assert items == []

    def test_mixed_metadata_and_real_content(self):
        """metadata ノイズと実コンテンツが混在しても実コンテンツだけ抽出されること."""
        content = (
            "#22 Meeting Transcript:\n"
            "New Podcast Processed\n"
            "Description: <p>今後の方針を確認する必要があります</p>\n"
            "URL: https://example.com/episode/22\n"
            "TODO: Cloud Scheduler の設定を確認する\n"
            "アーキテクチャの方針はどう設計すべきか?"
        )
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        items = analyzer.extract_action_items(episodes)
        prompts = analyzer.extract_discussion_prompts(episodes)

        # metadata は除外され、実コンテンツのみ抽出される
        assert len(items) == 1
        assert "TODO" in items[0].text
        assert all("Description" not in item.text for item in items)
        assert all("URL" not in item.text for item in items)
        assert all("New Podcast" not in item.text for item in items)
        assert len(prompts) >= 1
        assert any(p.prompt_type == PromptType.design_decision for p in prompts)

    def test_prompts_count_reduced_vs_noisy_baseline(self):
        """metadata を含む episode でも noise 除去後の prompts 件数が合理的範囲に収まること."""
        # metadata ノイズを多数含む content
        content = (
            "#22 Meeting Transcript:\n"
            "New Podcast Processed\n"
            "Description: <p>今後の方針を検討する。将来的な設計方針はどうするか</p>\n"
            "URL: https://example.com/episode/22\n"
            "https://another-link.com/episode?utm_source=rss\n"
            # 実コンテンツ
            "AI / LLM を活用したアジェンダ生成を今後進めたい。\n"
            "アーキテクチャの設計はどう実装すべきか?\n"
        )
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        # metadata 行は除外されるため、実コンテンツ由来のみ: 最大 2 件程度
        assert len(prompts) <= 3


class TestDiscussionPromptNoiseFiltering:
    """discussion_prompts の noise guard / minimum length テストクラス."""

    def test_very_short_sentence_not_extracted(self):
        """6 文字以下の文(閾値未満)が discussion_prompt に含まれないこと."""
        # "設計?" = 3 chars → noise
        content = "#1 Meeting Transcript:\n設計?"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert prompts == []

    def test_9char_uncertain_sentence_is_extracted(self):
        """9 文字の文(閾値以上)が正しく抽出されること."""
        # "どう設計すべきか?" = 9 chars — 7 文字閾値をちょうど超える
        content = "#1 Meeting Transcript:\nどう設計すべきか?"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert len(prompts) >= 1

    def test_normal_uncertain_sentence_extracted(self):
        """11 文字以上の uncertain 行が正しく抽出されること."""
        # "詳細はまだ検討中です。" = 11 chars
        content = "#1 Meeting Transcript:\n詳細はまだ検討中です。"
        episodes = _make_episodes_from_content(content)
        analyzer = TranscriptAnalyzer()

        prompts = analyzer.extract_discussion_prompts(episodes)

        assert any(p.prompt_type == PromptType.uncertain for p in prompts)


class TestPhase1BIntegration:
    """Phase 1-B 全体パイプラインの integration テスト."""

    def test_full_pipeline_two_episodes(self):
        """reconstruct -> extract_all -> build_agenda の全パイプラインが通ること."""
        episodes = _make_episodes_from_content(_EP1_CONTENT, _EP2_CONTENT)
        analyzer = TranscriptAnalyzer()

        themes = analyzer.extract_recurring_themes(episodes)
        items = analyzer.extract_action_items(episodes)
        prompts = analyzer.extract_discussion_prompts(episodes)

        result = analyzer.build_agenda(
            episodes=episodes,
            recurring_themes=themes,
            action_items=items,
            discussion_prompts=prompts,
            generated_at="2024-01-15T00:00:00+00:00",
            analysis_window_size=50,
            fetched_message_count=2,
        )

        # 基本的な整合性チェック
        assert result.analyzed_episodes == 2
        assert len(result.recurring_themes) >= 1
        assert len(result.action_items) >= 1
        assert len(result.discussion_prompts) >= 1
        assert result.schema_version == "1.0"

    def test_full_pipeline_result_is_json_serializable(self):
        """full pipeline の結果が JSON-serializable であること."""
        episodes = _make_episodes_from_content(_EP1_CONTENT, _EP2_CONTENT)
        analyzer = TranscriptAnalyzer()

        themes = analyzer.extract_recurring_themes(episodes)
        items = analyzer.extract_action_items(episodes)
        prompts = analyzer.extract_discussion_prompts(episodes)

        result = analyzer.build_agenda(
            episodes=episodes,
            recurring_themes=themes,
            action_items=items,
            discussion_prompts=prompts,
            generated_at="2024-01-15T00:00:00+00:00",
            analysis_window_size=50,
            fetched_message_count=2,
        )

        d = result.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(json_str)

        # metadata の検証
        assert parsed["metadata"]["fetched_message_count"] == 2
        assert parsed["metadata"]["analysis_window_size"] == 50
        # themes に score が含まれること
        for theme in parsed["recurring_themes"]:
            assert theme["score"] is not None
