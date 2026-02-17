"use client";

import { useState } from "react";
import EpisodeFilters from "@/components/episode-filters";
import EpisodeList from "@/components/episode-list";
import PodcastEditor from "@/components/podcast-editor";
import {
  Episode,
  Podcast,
  fetchEpisodes,
  importFeed,
  publishRss,
  updateEpisode,
  updatePodcast,
} from "@/services/api";

export default function HomePage() {
  const [rssUrl, setRssUrl] = useState("");
  const [podcast, setPodcast] = useState<Podcast | null>(null);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const loadFeed = async () => {
    try {
      const data = await importFeed(rssUrl);
      setPodcast(data.podcast);
      setEpisodes(data.episodes);
      setMessage("RSSを読み込みました。");
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "読み込みに失敗しました",
      );
    }
  };

  const refreshEpisodes = async (nextQuery = query, nextStatus = status) => {
    if (!podcast) return;
    const list = await fetchEpisodes(podcast.id, {
      q: nextQuery,
      status: nextStatus,
    });
    setEpisodes(list);
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-10">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold">Podcast UI Editor</h1>
        <p className="text-sm text-slate-600">
          RSSを読み込み、番組・エピソードを編集します。
        </p>
      </header>

      <section className="space-y-3 rounded-md bg-white p-4 shadow">
        <label className="block text-sm">
          RSS URL
          <input
            className="mt-1 w-full rounded border px-3 py-2"
            value={rssUrl}
            onChange={(event) => setRssUrl(event.target.value)}
          />
        </label>
        <button
          className="rounded bg-slate-900 px-4 py-2 text-sm text-white"
          onClick={loadFeed}
        >
          RSSを読み込む
        </button>
      </section>

      {message ? <p className="text-sm text-blue-600">{message}</p> : null}

      {podcast ? (
        <>
          <PodcastEditor
            podcast={podcast}
            onSave={async (data) => {
              const updated = await updatePodcast(podcast.id, data);
              setPodcast(updated);
              setMessage("番組情報を更新しました。");
            }}
          />

          <EpisodeFilters
            query={query}
            status={status}
            onChange={async (next) => {
              setQuery(next.query);
              setStatus(next.status);
              await refreshEpisodes(next.query, next.status);
            }}
          />

          <EpisodeList
            episodes={episodes}
            onSave={async (episodeId, data) => {
              if (!podcast) return;
              await updateEpisode(podcast.id, episodeId, data);
              await refreshEpisodes();
              setMessage("エピソードを更新しました。");
            }}
          />

          <button
            className="rounded bg-emerald-600 px-4 py-2 text-sm text-white"
            onClick={async () => {
              if (!podcast) return;
              const result = await publishRss(podcast.id);
              setMessage(`RSSを公開しました: ${result.rssUrl}`);
            }}
          >
            RSSを公開する
          </button>
        </>
      ) : null}
    </div>
  );
}
