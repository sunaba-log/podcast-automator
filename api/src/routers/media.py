from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel

from src.middleware.auth import require_admin_password
from src.services.media_uploader import upload_audio, upload_image
from src.services.rss_parser import (
    update_episode_artwork,
    update_episode_audio,
    update_podcast_artwork,
)

router = APIRouter(
    prefix="/api/podcasts/{podcastId}",
    tags=["media"],
    dependencies=[Depends(require_admin_password)],
)


class ImageUploadResponse(BaseModel):
    imageUrl: str


class AudioUploadResponse(BaseModel):
    audioUrl: str
    audioSizeBytes: int


@router.post("/artwork", response_model=ImageUploadResponse)
async def upload_podcast_artwork(podcastId: str, file: UploadFile) -> ImageUploadResponse:
    data = await file.read()
    image_url = upload_image(podcastId, file.filename or "artwork", file.content_type or "", data)
    update_podcast_artwork(podcastId, image_url)
    return ImageUploadResponse(imageUrl=image_url)


@router.post("/episodes/{episodeId}/artwork", response_model=ImageUploadResponse)
async def upload_episode_artwork(
    podcastId: str, episodeId: str, file: UploadFile
) -> ImageUploadResponse:
    data = await file.read()
    image_url = upload_image(episodeId, file.filename or "artwork", file.content_type or "", data)
    update_episode_artwork(podcastId, episodeId, image_url)
    return ImageUploadResponse(imageUrl=image_url)


@router.post("/episodes/{episodeId}/audio", response_model=AudioUploadResponse)
async def upload_episode_audio(
    podcastId: str, episodeId: str, audioFile: UploadFile
) -> AudioUploadResponse:
    data = await audioFile.read()
    audio_url, audio_size = upload_audio(
        episodeId, audioFile.filename or "audio", audioFile.content_type or "", data
    )
    update_episode_audio(podcastId, episodeId, audio_url, audio_size, audioFile.content_type)
    return AudioUploadResponse(audioUrl=audio_url, audioSizeBytes=audio_size)
