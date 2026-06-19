from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.episode_repository import PostgresEpisodeRepository


def _connection_with_rowcount(rowcount: int = 1) -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.rowcount = rowcount
    cursor_context = MagicMock()
    cursor_context.__enter__.return_value = cursor
    connection = MagicMock()
    connection.cursor.return_value = cursor_context
    connection_context = MagicMock()
    connection_context.__enter__.return_value = connection
    return connection_context, cursor


def test_mark_processing_updates_expected_episode() -> None:
    connection, cursor = _connection_with_rowcount()

    with patch("infrastructure.episode_repository.psycopg.connect", return_value=connection) as connect:
        PostgresEpisodeRepository(database_url="postgresql://example").mark_processing(
            podcast_id=1,
            episode_id=42,
            source_audio_path="podcasts/1/episodes/42/source/audio.mp3",
        )

    connect.assert_called_once_with("postgresql://example")
    parameters = cursor.execute.call_args.args[1]
    assert parameters == ("podcasts/1/episodes/42/source/audio.mp3", 1, 42)


def test_repository_raises_when_episode_does_not_exist() -> None:
    connection, _cursor = _connection_with_rowcount(0)

    with (
        patch("infrastructure.episode_repository.psycopg.connect", return_value=connection),
        pytest.raises(LookupError, match="podcast_id=1, episode_id=42"),
    ):
        PostgresEpisodeRepository(database_url="postgresql://example").mark_failed(
            podcast_id=1,
            episode_id=42,
            error_message="failed",
        )
