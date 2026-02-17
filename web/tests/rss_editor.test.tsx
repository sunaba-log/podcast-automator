import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PodcastEditor from "@/components/podcast-editor";

const samplePodcast = {
  id: "podcast-1",
  title: "Sample",
  description: "Description",
  rssUrl: "https://example.com/rss",
};

describe("PodcastEditor", () => {
  it("edits and saves podcast info", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<PodcastEditor podcast={samplePodcast} onSave={onSave} />);

    fireEvent.change(screen.getByLabelText("タイトル"), {
      target: { value: "New Title" },
    });
    fireEvent.click(screen.getByText("保存"));

    expect(onSave).toHaveBeenCalledWith({
      title: "New Title",
      description: "Description",
    });
  });
});
