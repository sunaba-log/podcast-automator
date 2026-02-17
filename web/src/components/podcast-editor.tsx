"use client";

import { useState } from "react";
import type { Podcast } from "@/services/api";

type Props = {
  podcast: Podcast;
  onSave: (data: Partial<Podcast>) => Promise<void>;
};

export default function PodcastEditor({ podcast, onSave }: Props) {
  const [title, setTitle] = useState(podcast.title);
  const [description, setDescription] = useState(podcast.description);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    await onSave({ title, description });
    setSaving(false);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-md bg-white p-4 shadow"
    >
      <h2 className="text-lg font-semibold">番組情報</h2>
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
          rows={4}
        />
      </label>
      <button
        type="submit"
        className="rounded bg-blue-600 px-4 py-2 text-sm text-white"
        disabled={saving}
      >
        {saving ? "保存中..." : "保存"}
      </button>
    </form>
  );
}
