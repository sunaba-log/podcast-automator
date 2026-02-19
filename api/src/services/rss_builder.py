from __future__ import annotations

from email.utils import parsedate_to_datetime

from feedgen.feed import FeedGenerator

from src.schemas.episode import Episode
from src.schemas.podcast import Podcast


def build_rss_xml(podcast: Podcast, episodes: list[Episode]) -> str:
    fg = FeedGenerator()
    fg.title(podcast.title)
    fg.description(podcast.description)
    fg.link(href=podcast.link or podcast.rssUrl, rel="alternate")
    fg.language(podcast.language or "ja")

    # Podcast拡張機能(iTunesタグなど)を読み込む
    fg.load_extension("podcast")
    # Dublin Core拡張機能(作成者タグなど)を読み込む
    fg.load_extension("dc")

    if podcast.itunesImageUrl:
        try:
            fg.image(
                url=podcast.itunesImageUrl, title=podcast.title, link=podcast.link or podcast.rssUrl
            )
        except ValueError:
            pass

    for episode in episodes:
        entry = fg.add_entry()
        entry.id(episode.id)
        entry.title(episode.title)
        entry.description(episode.description)
        if episode.audioUrl:
            entry.enclosure(
                episode.audioUrl,
                str(episode.audioSizeBytes or 0),
                episode.audioMimeType or "audio/mpeg",
            )

        # iTunes拡張タグ
        if episode.itunesImageUrl:
            entry.podcast.itunes_image(episode.itunesImageUrl)
        if episode.itunesDuration:
            entry.podcast.itunes_duration(episode.itunesDuration)
        if episode.itunesExplicit:
            entry.podcast.itunes_explicit(episode.itunesExplicit)
        if episode.itunesSummary:
            entry.summary(episode.itunesSummary)
        if episode.itunesEpisodeType:
            # itunes:episodeType タグを直接設定
            pass  # feedgenは現時点でこのタグをサポートしていない
        if episode.itunesSeason is not None:
            entry.podcast.itunes_season(episode.itunesSeason)
        if episode.itunesEpisode is not None:
            entry.podcast.itunes_episode(episode.itunesEpisode)

        # Dublin Core作成者タグ
        if episode.dcCreator:
            entry.dc.dc_creator(episode.dcCreator)

        if episode.publishedAt:
            try:
                entry.pubDate(parsedate_to_datetime(episode.publishedAt))
            except (TypeError, ValueError):
                pass

    return fg.rss_str(pretty=True).decode("utf-8")
