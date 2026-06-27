from __future__ import annotations

import pytest

from domain.models import EpisodeObjectReference


@pytest.mark.parametrize(
    ("object_path", "expected_filename"),
    [
        ("podcasts/1/episodes/42/source/recording.mp3", "recording.mp3"),
        ("podcasts/1/episodes/42/source/recording.m4a", "recording.m4a"),
        ("podcasts/1/episodes/42/source/recording.wav", "recording.wav"),
        ("podcasts/1/episodes/42/source/recording.flac", "recording.flac"),
        ("podcasts/1/episodes/42/source/recording.MP3", "recording.MP3"),
    ],
)
def test_parse_episode_object_reference(object_path: str, expected_filename: str) -> None:
    reference = EpisodeObjectReference.parse(object_path)

    assert reference.podcast_id == 1
    assert reference.episode_id == 42
    assert reference.filename == expected_filename


@pytest.mark.parametrize(
    "object_path",
    [
        "recording.mp3",
        "podcasts/0/episodes/42/source/recording.mp3",
        "podcasts/1/episodes/0/source/recording.mp3",
        "podcasts/1/episodes/42/recording.mp3",
        "podcasts/1/episodes/42/source/nested/recording.mp3",
        "podcasts/1/episodes/42/source/recording.ogg",
    ],
)
def test_parse_rejects_paths_outside_contract(object_path: str) -> None:
    with pytest.raises(ValueError, match="GCS object path must match"):
        EpisodeObjectReference.parse(object_path)
