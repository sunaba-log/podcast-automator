from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Iterable

import feedparser

from src.errors import AppError
from src.schemas.episode import Episode
from src.schemas.podcast import Podcast


@dataclass
class RssStore:
    podcast: Podcast | None = None
    episodes: dict[str, Episode] = field(default_factory=dict)


_STORE = RssStore()


def _make_podcast_id(rss_url: str) -> str:
    return hashlib.sha1(rss_url.encode("utf-8")).hexdigest()[:12]


def import_feed(rss_url: str) -> tuple[Podcast, list[Episode]]:
    parsed = feedparser.parse(rss_url)
    if parsed.bozo:
        raise AppError("RSSの解析に失敗しました", status_code=400)
    feed = parsed.feed
    podcast_id = _make_podcast_id(rss_url)
    podcast = Podcast(
        id=podcast_id,
        title=feed.get("title", ""),
        description=feed.get("subtitle", "") or feed.get("description", ""),
        rssUrl=rss_url,
        link=feed.get("link"),
        language=feed.get("language"),
        itunesAuthor=feed.get("author"),
        itunesCategory=feed.get("itunes_category"),
        itunesImageUrl=feed.get("image", {}).get("href")
        if isinstance(feed.get("image"), dict)
        else None,
        itunesExplicit=feed.get("itunes_explicit"),
        ownerName=feed.get("itunes_owner", {}).get("name")
        if isinstance(feed.get("itunes_owner"), dict)
        else None,
        ownerEmail=feed.get("itunes_owner", {}).get("email")
        if isinstance(feed.get("itunes_owner"), dict)
        else None,
    )
    episodes = _build_episodes(podcast_id, parsed.entries)
    _STORE.podcast = podcast
    _STORE.episodes = {episode.id: episode for episode in episodes}
    return podcast, episodes


def _build_episodes(podcast_id: str, entries: Iterable[dict]) -> list[Episode]:
    result: list[Episode] = []
    for entry in entries:
        entry_id = entry.get("id") or entry.get("guid") or entry.get("link") or ""
        audio_url = ""
        audio_size = None
        audio_mime = None
        if entry.get("enclosures"):
            enclosure = entry.get("enclosures")[0]
            audio_url = enclosure.get("href", "")
            if enclosure.get("length"):
                try:
                    audio_size = int(enclosure.get("length"))
                except (TypeError, ValueError):
                    audio_size = None
            audio_mime = enclosure.get("type")
        # iTunesの画像を取得
        itunes_image = None
        if entry.get("image"):
            if isinstance(entry.get("image"), dict):
                itunes_image = entry.get("image").get("href")
            elif isinstance(entry.get("image"), str):
                itunes_image = entry.get("image")

        # シーズンとエピソード番号を取得
        season = None
        episode_num = None
        if entry.get("itunes_season"):
            try:
                season = int(entry.get("itunes_season"))
            except (TypeError, ValueError):
                pass
        if entry.get("itunes_episode"):
            try:
                episode_num = int(entry.get("itunes_episode"))
            except (TypeError, ValueError):
                pass

        # summaryを取得（itunes_summaryが空の場合はsummaryを使用）
        summary = entry.get("summary", "")
        itunes_summary = entry.get("itunes_summary") or summary

        result.append(
            Episode(
                id=entry_id,
                podcastId=podcast_id,
                title=entry.get("title", ""),
                description=summary,
                status="published",
                audioUrl=audio_url,
                audioSizeBytes=audio_size,
                audioMimeType=audio_mime,
                itunesDuration=entry.get("itunes_duration"),
                itunesImageUrl=itunes_image,
                itunesExplicit=entry.get("itunes_explicit") or "no",
                itunesSummary=itunes_summary,
                itunesEpisodeType=entry.get("itunes_episodetype"),
                itunesSeason=season,
                itunesEpisode=episode_num,
                dcCreator=entry.get("author"),
                publishedAt=entry.get("published"),
            )
        )
    return result


def get_podcast(podcast_id: str) -> Podcast:
    if not _STORE.podcast or _STORE.podcast.id != podcast_id:
        raise AppError("Podcastが見つかりません", status_code=404)
    return _STORE.podcast


def update_podcast(podcast_id: str, payload: dict) -> Podcast:
    podcast = get_podcast(podcast_id)
    updated = podcast.model_copy(update=payload)
    _STORE.podcast = updated
    return updated


def list_episodes(
    podcast_id: str, q: str | None = None, status: str | None = None
) -> list[Episode]:
    if not _STORE.podcast or _STORE.podcast.id != podcast_id:
        raise AppError("Podcastが見つかりません", status_code=404)
    episodes = list(_STORE.episodes.values())
    if q:
        episodes = [episode for episode in episodes if q.lower() in episode.title.lower()]
    if status:
        episodes = [episode for episode in episodes if episode.status == status]
    return episodes


def update_episode(podcast_id: str, episode_id: str, payload: dict) -> Episode:
    if not _STORE.podcast or _STORE.podcast.id != podcast_id:
        raise AppError("Podcastが見つかりません", status_code=404)
    episode = _STORE.episodes.get(episode_id)
    if not episode:
        raise AppError("Episodeが見つかりません", status_code=404)
    updated = episode.model_copy(update=payload)
    _STORE.episodes[episode_id] = updated
    return updated


def update_podcast_artwork(podcast_id: str, image_url: str) -> Podcast:
    podcast = get_podcast(podcast_id)
    updated = podcast.model_copy(update={"itunesImageUrl": image_url})
    _STORE.podcast = updated
    return updated


def update_episode_artwork(podcast_id: str, episode_id: str, image_url: str) -> Episode:
    return update_episode(podcast_id, episode_id, {"itunesImageUrl": image_url})


def update_episode_audio(
    podcast_id: str,
    episode_id: str,
    audio_url: str,
    audio_size: int | None,
    audio_mime: str | None,
) -> Episode:
    return update_episode(
        podcast_id,
        episode_id,
        {"audioUrl": audio_url, "audioSizeBytes": audio_size, "audioMimeType": audio_mime},
    )


def create_episode(
    podcast_id: str,
    title: str,
    description: str,
    status: str,
    audio_url: str,
    audio_size: int | None,
    audio_mime: str | None,
) -> Episode:
    if not _STORE.podcast or _STORE.podcast.id != podcast_id:
        raise AppError("Podcastが見つかりません", status_code=404)
    episode_id = hashlib.sha1(f"{podcast_id}:{title}:{audio_url}".encode("utf-8")).hexdigest()[:12]
    episode = Episode(
        id=episode_id,
        podcastId=podcast_id,
        title=title,
        description=description,
        status=status,
        audioUrl=audio_url,
        audioSizeBytes=audio_size,
        audioMimeType=audio_mime,
        itunesDuration=None,
        itunesImageUrl=None,
        itunesExplicit=None,
        itunesSummary=None,
        itunesEpisodeType=None,
        itunesSeason=None,
        itunesEpisode=None,
        dcCreator=None,
        publishedAt=None,
    )
    _STORE.episodes[episode_id] = episode
    return episode
