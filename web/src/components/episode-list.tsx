"use client";

import { useState } from "react";
import type { Episode } from "@/services/api";
import ArtworkUploader from "@/components/artwork-uploader";
import AudioUploader from "@/components/audio-uploader";

type Props = {
  episodes: Episode[];
  onSave: (episodeId: string, data: Partial<Episode>) => Promise<void>;
  onUploadArtwork: (episodeId: string, file: File) => Promise<void>;
  onUploadAudio: (episodeId: string, file: File) => Promise<void>;
};

export default function EpisodeList({
  episodes,
  onSave,
  onUploadArtwork,
  onUploadAudio,
}: Props) {
  const [pendingId, setPendingId] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      {episodes.map((episode) => (
        <EpisodeCard
          key={episode.id}
          episode={episode}
          onSave={async (data) => {
            setPendingId(episode.id);
            await onSave(episode.id, data);
            setPendingId(null);
          }}
          onUploadArtwork={onUploadArtwork}
          onUploadAudio={onUploadAudio}
          saving={pendingId === episode.id}
        />
      ))}
    </div>
  );
}

function EpisodeCard({
  episode,
  onSave,
  onUploadArtwork,
  onUploadAudio,
  saving,
}: {
  episode: Episode;
  onSave: (data: Partial<Episode>) => Promise<void>;
  onUploadArtwork: (episodeId: string, file: File) => Promise<void>;
  onUploadAudio: (episodeId: string, file: File) => Promise<void>;
  saving: boolean;
}) {
  const [title, setTitle] = useState(episode.title);
  const [description, setDescription] = useState(episode.description);
  const [status, setStatus] = useState(episode.status);

  return (
    <form
      className="space-y-2 rounded-md bg-white p-4 shadow"
      onSubmit={(event) => {
        event.preventDefault();
        onSave({ title, description, status });
      }}
    >
      <h3 className="text-sm font-semibold">{episode.title}</h3>
      <label className="block text-sm">
        タイトル
        <input
          className="mt-1 w-full rounded border px-3 py-2"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
      </label>
      <label className="block text-sm">
        説明文
        <textarea
          className="mt-1 w-full rounded border px-3 py-2"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
        />
      </label>
      <label className="block text-sm">
        配信状態
        <select
          className="mt-1 w-full rounded border px-3 py-2"
          value={status}
          onChange={(event) =>
            setStatus(event.target.value as Episode["status"])
          }
        >
          <option value="draft">下書き</option>
          <option value="published">公開</option>
        </select>
      </label>
      <ArtworkUploader
        label="エピソード画像"
        onUpload={(file) => onUploadArtwork(episode.id, file)}
      />
      <AudioUploader
        label="音声差し替え"
        onUpload={(file) => onUploadAudio(episode.id, file)}
      />
      <button
        className="rounded bg-slate-800 px-3 py-2 text-sm text-white"
        disabled={saving}
      >
        {saving ? "保存中..." : "エピソードを保存"}
      </button>
    </form>
  );
}
