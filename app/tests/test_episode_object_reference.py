from __future__ import annotations

import pytest

from domain.models import EpisodeObjectReference


def test_parse_episode_object_reference() -> None:
    reference = EpisodeObjectReference.parse("podcasts/1/episodes/42/source/recording.mp3")

    assert reference.podcast_id == 1
    assert reference.episode_id == 42
    assert reference.filename == "recording.mp3"


@pytest.mark.parametrize(
    "object_path",
    [
        "recording.mp3",
        "podcasts/0/episodes/42/source/recording.mp3",
        "podcasts/1/episodes/0/source/recording.mp3",
        "podcasts/1/episodes/42/recording.mp3",
        "podcasts/1/episodes/42/source/nested/recording.mp3",
        "podcasts/1/episodes/42/source/recording.wav",
    ],
)
def test_parse_rejects_paths_outside_contract(object_path: str) -> None:
    with pytest.raises(ValueError, match="GCS object path must match"):
        EpisodeObjectReference.parse(object_path)
