"use client";

import { useState } from "react";

type Props = {
  label: string;
  onUpload: (file: File) => Promise<void>;
};

export default function AudioUploader({ label, onUpload }: Props) {
  const [pending, setPending] = useState(false);

  return (
    <label className="flex items-center gap-3 text-sm">
      {label}
      <input
        type="file"
        accept="audio/mpeg,audio/mp4"
        disabled={pending}
        onChange={async (event) => {
          const file = event.target.files?.[0];
          if (!file) return;
          setPending(true);
          await onUpload(file);
          setPending(false);
          if (event.currentTarget) {
            event.currentTarget.value = "";
          }
        }}
      />
    </label>
  );
}
