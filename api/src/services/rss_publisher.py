from __future__ import annotations

from email.utils import parsedate_to_datetime

from feedgen.feed import FeedGenerator

from src.config import get_settings
from src.errors import AppError
from src.schemas.rss import PublishResult
from src.services.r2_client import R2Client
from src.services.rss_backup import create_backup
from src.services.rss_parser import get_podcast, list_episodes


def publish_rss(podcast_id: str) -> PublishResult:
    podcast = get_podcast(podcast_id)
    episodes = list_episodes(podcast_id)
    fg = FeedGenerator()
    fg.title(podcast.title)
    fg.description(podcast.description)
    fg.link(href=podcast.link or podcast.rssUrl, rel="alternate")
    fg.language(podcast.language or "ja")

    for episode in episodes:
        entry = fg.add_entry()
        entry.id(episode.id)
        entry.title(episode.title)
        entry.description(episode.description)
        entry.link(href=episode.audioUrl)
        if episode.publishedAt:
            try:
                entry.pubDate(parsedate_to_datetime(episode.publishedAt))
            except (TypeError, ValueError):
                pass

    raw_xml = fg.rss_str(pretty=True).decode("utf-8")
    backup = create_backup(podcast.rssUrl, raw_xml)

    settings = get_settings()
    if settings.r2_bucket_name and settings.r2_public_base_url:
        key = f"feeds/{podcast.id}.xml"
        R2Client().upload_bytes(key, raw_xml.encode("utf-8"), "application/rss+xml")
        rss_url = f"{settings.r2_public_base_url.rstrip('/')}/{key}"
    else:
        rss_url = podcast.rssUrl

    if not rss_url:
        raise AppError("RSS公開先が未設定です", status_code=400)

    return PublishResult(rssUrl=rss_url, backup=backup)
