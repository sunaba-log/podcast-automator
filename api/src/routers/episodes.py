from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel

from src.middleware.auth import require_admin_password
from src.schemas.episode import Episode
from src.services.media_uploader import upload_audio
from src.services.rss_parser import create_episode, list_episodes, update_episode

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


@router.post("", response_model=Episode, status_code=201)
async def create_episode_item(
    podcastId: str,
    title: str = Form(...),
    description: str = Form(...),
    status: str = Form("draft"),
    audioFile: UploadFile = File(...),
) -> Episode:
    data = await audioFile.read()
    audio_url, audio_size = upload_audio(
        podcastId, audioFile.filename or "audio", audioFile.content_type or "", data
    )
    return create_episode(
        podcastId,
        title=title,
        description=description,
        status=status,
        audio_url=audio_url,
        audio_size=audio_size,
        audio_mime=audioFile.content_type,
    )
