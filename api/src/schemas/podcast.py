from __future__ import annotations

from pydantic import BaseModel


class Podcast(BaseModel):
    id: str
    title: str
    description: str
    rssUrl: str
    link: str | None = None
    language: str | None = None
    itunesAuthor: str | None = None
    itunesCategory: str | None = None
    itunesImageUrl: str | None = None
    itunesExplicit: str | None = None
    ownerName: str | None = None
    ownerEmail: str | None = None
