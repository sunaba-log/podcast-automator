"use client";

type Props = {
  query: string;
  status: string;
  onChange: (next: { query: string; status: string }) => void;
};

export default function EpisodeFilters({ query, status, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-3 rounded-md bg-white p-4 shadow">
      <input
        className="flex-1 rounded border px-3 py-2"
        placeholder="検索"
        value={query}
        onChange={(event) => onChange({ query: event.target.value, status })}
      />
      <select
        className="rounded border px-3 py-2"
        value={status}
        onChange={(event) => onChange({ query, status: event.target.value })}
      >
        <option value="">すべて</option>
        <option value="draft">下書き</option>
        <option value="published">公開</option>
      </select>
    </div>
  );
}
