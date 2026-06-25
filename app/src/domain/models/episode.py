"""Episode identifiers shared across storage and database boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass

_EPISODE_OBJECT_PATH = re.compile(
    r"^podcasts/(?P<podcast_id>[1-9]\d*)/episodes/(?P<episode_id>[1-9]\d*)/source/(?P<filename>[^/]+\.mp3)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EpisodeObjectReference:
    """Identifiers encoded in a podcast source object path."""

    podcast_id: int
    episode_id: int
    filename: str
    object_path: str

    @classmethod
    def parse(cls, object_path: str) -> EpisodeObjectReference:
        """Parse the cross-repository GCS object path contract."""
        match = _EPISODE_OBJECT_PATH.fullmatch(object_path)
        if match is None:
            msg = "GCS object path must match podcasts/{podcast_id}/episodes/{episode_id}/source/{filename}.mp3"
            raise ValueError(msg)

        return cls(
            podcast_id=int(match.group("podcast_id")),
            episode_id=int(match.group("episode_id")),
            filename=match.group("filename"),
            object_path=object_path,
        )
