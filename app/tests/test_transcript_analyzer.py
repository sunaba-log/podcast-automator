"""TranscriptAnalyzer のユニットテスト."""

import json

import pytest

from services.discord_fetcher import DiscordMessage
from services.transcript_analyzer import (
    Episode,
    SortPolicy,
    TranscriptAnalyzer,
    TranscriptBoundaryError,
)


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
        episodes, warnings = analyzer.reconstruct_episodes(messages, strict=False)

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
            _msg(msg_id="1", content="#1 Meeting Transcript:\nContent", timestamp="2024-01-01T00:00:00Z", author_name="bot"),
            _msg(msg_id="2", content="continuation", timestamp="2024-01-01T00:01:00Z", author_name="someone_else"),
        ]
        episodes, warnings = analyzer.reconstruct_episodes(messages)

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
