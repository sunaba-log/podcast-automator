from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.middleware.auth import require_admin_password
from src.schemas.episode import Episode
from src.schemas.podcast import Podcast
from src.services.rss_parser import import_feed

router = APIRouter(
    prefix="/api/feeds", tags=["feeds"], dependencies=[Depends(require_admin_password)]
)


class ImportRequest(BaseModel):
    rssUrl: str


class ImportResponse(BaseModel):
    podcast: Podcast
    episodes: list[Episode]


@router.post("/import", response_model=ImportResponse)
def import_rss(request: ImportRequest) -> ImportResponse:
    podcast, episodes = import_feed(request.rssUrl)
    return ImportResponse(podcast=podcast, episodes=episodes)
