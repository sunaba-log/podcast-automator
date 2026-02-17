from __future__ import annotations

from fastapi import APIRouter, Depends

from src.middleware.auth import require_admin_password
from src.schemas.rss import PublishResult
from src.services.rss_publisher import publish_rss

router = APIRouter(
    prefix="/api/podcasts/{podcastId}/rss",
    tags=["rss"],
    dependencies=[Depends(require_admin_password)],
)


@router.post("/publish", response_model=PublishResult)
def publish_rss_feed(podcastId: str) -> PublishResult:
    return publish_rss(podcastId)
