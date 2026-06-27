"""Cloud SQL persistence for podcast episode processing state."""

from __future__ import annotations

from typing import Any

import psycopg


class PostgresEpisodeRepository:
    """Update episode records through a PostgreSQL connection string."""

    def __init__(self, *, database_url: str) -> None:
        """Initialize the repository."""
        self._database_url = database_url

    def mark_processing(self, *, podcast_id: str, episode_id: str, source_audio_path: str) -> None:
        """Mark an uploaded episode as processing."""
        self._execute_update(
            """
            UPDATE episodes
            SET status = 'processing',
                source_audio_path = COALESCE(source_audio_path, %s),
                processing_error = NULL,
                processing_started_at = now(),
                updated_at = now()
            WHERE podcast_id = %s AND episode_id = %s
            """,
            (source_audio_path, podcast_id, episode_id),
            podcast_id=podcast_id,
            episode_id=episode_id,
        )

    def mark_completed(
        self,
        *,
        podcast_id: str,
        episode_id: str,
        title: str,
        description: str,
        audio_url: str,
        duration_seconds: int | None,
    ) -> None:
        """Store generated metadata and mark an episode complete."""
        self._execute_update(
            """
            UPDATE episodes
            SET status = 'completed',
                title = %s,
                description = %s,
                audio_file_path = %s,
                duration_seconds = %s,
                processing_error = NULL,
                processing_completed_at = now(),
                published_at = COALESCE(published_at, now()),
                updated_at = now()
            WHERE podcast_id = %s AND episode_id = %s
            """,
            (title, description, audio_url, duration_seconds, podcast_id, episode_id),
            podcast_id=podcast_id,
            episode_id=episode_id,
        )

    def mark_failed(self, *, podcast_id: str, episode_id: str, error_message: str) -> None:
        """Record a processing failure."""
        self._execute_update(
            """
            UPDATE episodes
            SET status = 'failed',
                processing_error = %s,
                processing_completed_at = now(),
                updated_at = now()
            WHERE podcast_id = %s AND episode_id = %s
            """,
            (error_message[:2000], podcast_id, episode_id),
            podcast_id=podcast_id,
            episode_id=episode_id,
        )

    def _execute_update(
        self,
        statement: str,
        parameters: tuple[Any, ...],
        *,
        podcast_id: str,
        episode_id: str,
    ) -> None:
        with psycopg.connect(self._database_url) as connection, connection.cursor() as cursor:
            cursor.execute(statement, parameters)
            if cursor.rowcount != 1:
                msg = f"Episode not found: podcast_id={podcast_id}, episode_id={episode_id}"
                raise LookupError(msg)
