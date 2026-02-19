import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ArtworkUploader from "@/components/artwork-uploader";
import AudioUploader from "@/components/audio-uploader";
import EpisodeCreateForm from "@/components/episode-create-form";

describe("media upload components", () => {
  it("uploads artwork", async () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    render(<ArtworkUploader label="Artwork" onUpload={onUpload} />);
    const file = new File(["image"], "cover.jpg", { type: "image/jpeg" });

    fireEvent.change(screen.getByLabelText("Artwork"), {
      target: { files: [file] },
    });

    expect(onUpload).toHaveBeenCalledWith(file);
  });

  it("uploads audio", async () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    render(<AudioUploader label="Audio" onUpload={onUpload} />);
    const file = new File(["audio"], "clip.mp3", { type: "audio/mpeg" });

    fireEvent.change(screen.getByLabelText("Audio"), {
      target: { files: [file] },
    });

    expect(onUpload).toHaveBeenCalledWith(file);
  });

  it("creates episode", async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    render(<EpisodeCreateForm onCreate={onCreate} />);

    const file = new File(["audio"], "clip.mp3", { type: "audio/mpeg" });

    fireEvent.change(screen.getByPlaceholderText("タイトル"), {
      target: { value: "Ep" },
    });
    fireEvent.change(screen.getByPlaceholderText("説明文"), {
      target: { value: "Desc" },
    });

    // セレクトボックスを選択
    const statusSelect = screen.getByRole("combobox");
    fireEvent.change(statusSelect, {
      target: { value: "published" },
    });

    // ファイル入力を選択
    const fileInput = screen.getByLabelText("音声ファイル");
    fireEvent.change(fileInput, {
      target: { files: [file] },
    });

    // フォームを直接送信
    const form = screen.getByLabelText("episode-create-form");
    fireEvent.submit(form);

    expect(onCreate).toHaveBeenCalledWith({
      title: "Ep",
      description: "Desc",
      status: "published",
      audioFile: file,
    });
  });
});
