from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.middleware.auth import require_admin_password
from src.schemas.episode import Episode
from src.services.rss_parser import list_episodes, update_episode

router = APIRouter(
    prefix="/api/podcasts/{podcastId}/episodes",
    tags=["episodes"],
    dependencies=[Depends(require_admin_password)],
)


class EpisodeUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None


@router.get("", response_model=list[Episode])
def list_episode_items(
    podcastId: str,
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[Episode]:
    return list_episodes(podcastId, q=q, status=status)


@router.patch("/{episodeId}", response_model=Episode)
def update_episode_item(podcastId: str, episodeId: str, request: EpisodeUpdateRequest) -> Episode:
    return update_episode(podcastId, episodeId, request.model_dump(exclude_unset=True))
