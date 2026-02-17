from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.middleware.auth import require_admin_password
from src.schemas.podcast import Podcast
from src.services.rss_parser import get_podcast, update_podcast

router = APIRouter(
    prefix="/api/podcasts", tags=["podcasts"], dependencies=[Depends(require_admin_password)]
)


class PodcastUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    link: str | None = None
    itunesAuthor: str | None = None
    itunesCategory: str | None = None
    itunesImageUrl: str | None = None
    itunesExplicit: str | None = None
    ownerName: str | None = None
    ownerEmail: str | None = None


@router.get("/{podcastId}", response_model=Podcast)
def get_podcast_by_id(podcastId: str) -> Podcast:
    return get_podcast(podcastId)


@router.patch("/{podcastId}", response_model=Podcast)
def update_podcast_by_id(podcastId: str, request: PodcastUpdateRequest) -> Podcast:
    return update_podcast(podcastId, request.model_dump(exclude_unset=True))
