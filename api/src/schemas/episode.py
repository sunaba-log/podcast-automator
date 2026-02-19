from __future__ import annotations

from pydantic import BaseModel


class Episode(BaseModel):
    id: str
    podcastId: str
    title: str
    description: str
    status: str
    audioUrl: str
    audioSizeBytes: int | None = None
    audioMimeType: str | None = None
    itunesDuration: str | None = None
    itunesImageUrl: str | None = None
    itunesExplicit: str | None = None
    itunesSummary: str | None = None
    itunesEpisodeType: str | None = None
    itunesSeason: int | None = None
    itunesEpisode: int | None = None
    dcCreator: str | None = None
    publishedAt: str | None = None
