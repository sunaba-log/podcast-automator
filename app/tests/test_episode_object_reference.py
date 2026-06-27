from __future__ import annotations

import pytest

from domain.models import EpisodeObjectReference


@pytest.mark.parametrize(
    ("object_path", "expected_podcast_id", "expected_episode_id", "expected_filename"),
    [
        ("podcasts/1/episodes/42/source/recording.mp3", "1", "42", "recording.mp3"),
        ("podcasts/sunabalog/episodes/ep-2026-06/source/recording.m4a", "sunabalog", "ep-2026-06", "recording.m4a"),
        ("podcasts/podcast_dev/episodes/ep_123/source/recording.wav", "podcast_dev", "ep_123", "recording.wav"),
        (
            "podcasts/123e4567-e89b-12d3-a456-426614174000/episodes/ep1/source/recording.flac",
            "123e4567-e89b-12d3-a456-426614174000",
            "ep1",
            "recording.flac",
        ),
    ],
)
def test_parse_episode_object_reference(
    object_path: str, expected_podcast_id: str, expected_episode_id: str, expected_filename: str
) -> None:
    reference = EpisodeObjectReference.parse(object_path)

    assert reference.podcast_id == expected_podcast_id
    assert reference.episode_id == expected_episode_id
    assert reference.filename == expected_filename


@pytest.mark.parametrize(
    "object_path",
    [
        "recording.mp3",
        "podcasts/pod@cast/episodes/42/source/recording.mp3",
        "podcasts/1/episodes/ep#1/source/recording.mp3",
        "podcasts/1/episodes/42/recording.mp3",
        "podcasts/1/episodes/42/source/nested/recording.mp3",
        "podcasts/1/episodes/42/source/recording.ogg",
    ],
)
def test_parse_rejects_paths_outside_contract(object_path: str) -> None:
    with pytest.raises(ValueError, match="GCS object path must match"):
        EpisodeObjectReference.parse(object_path)
