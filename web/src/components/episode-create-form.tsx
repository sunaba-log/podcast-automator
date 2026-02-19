"use client";

import { useState } from "react";

export type EpisodeCreatePayload = {
  title: string;
  description: string;
  status: "draft" | "published";
  audioFile: File | null;
};

type Props = {
  onCreate: (payload: EpisodeCreatePayload) => Promise<void>;
};

export default function EpisodeCreateForm({ onCreate }: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<EpisodeCreatePayload["status"]>("draft");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setPending(true);
    await onCreate({ title, description, status, audioFile });
    setPending(false);
    setTitle("");
    setDescription("");
    setStatus("draft");
    setAudioFile(null);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-md bg-white p-4 shadow"
      aria-label="episode-create-form"
    >
      <h3 className="text-sm font-semibold">新規エピソード作成</h3>
      <input
        className="w-full rounded border px-3 py-2 text-sm"
        placeholder="タイトル"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        required
      />
      <textarea
        className="w-full rounded border px-3 py-2 text-sm"
        placeholder="説明文"
        rows={3}
        value={description}
        onChange={(event) => setDescription(event.target.value)}
        required
      />
      <select
        className="w-full rounded border px-3 py-2 text-sm"
        value={status}
        onChange={(event) =>
          setStatus(event.target.value as EpisodeCreatePayload["status"])
        }
      >
        <option value="draft">下書き</option>
        <option value="published">公開</option>
      </select>
      <label className="text-sm">
        音声ファイル
        <input
          className="mt-1 block"
          type="file"
          accept="audio/mpeg,audio/mp4"
          onChange={(event) => setAudioFile(event.target.files?.[0] ?? null)}
          required
        />
      </label>
      <button
        className="rounded bg-emerald-600 px-3 py-2 text-sm text-white"
        disabled={pending}
      >
        {pending ? "作成中..." : "作成"}
      </button>
    </form>
  );
}
