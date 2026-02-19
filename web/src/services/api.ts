export type Podcast = {
  id: string;
  title: string;
  description: string;
  rssUrl: string;
  link?: string | null;
  itunesAuthor?: string | null;
  itunesCategory?: string | null;
  itunesImageUrl?: string | null;
  itunesExplicit?: string | null;
  ownerName?: string | null;
  ownerEmail?: string | null;
};

export type Episode = {
  id: string;
  podcastId: string;
  title: string;
  description: string;
  status: "draft" | "published";
  audioUrl: string;
  audioSizeBytes?: number | null;
  audioMimeType?: string | null;
  itunesDuration?: string | null;
  itunesImageUrl?: string | null;
  publishedAt?: string | null;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ADMIN_PASSWORD = process.env.NEXT_PUBLIC_ADMIN_PASSWORD || "";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Password": ADMIN_PASSWORD,
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const payload = await response
      .json()
      .catch(() => ({ message: "Unknown error" }));
    throw new Error(payload.message || "Request failed");
  }

  return response.json() as Promise<T>;
}

async function formRequest<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
    headers: {
      "X-Admin-Password": ADMIN_PASSWORD,
    },
  });

  if (!response.ok) {
    const payload = await response
      .json()
      .catch(() => ({ message: "Unknown error" }));
    throw new Error(payload.message || "Request failed");
  }

  return response.json() as Promise<T>;
}

export async function importFeed(
  rssUrl: string,
): Promise<{ podcast: Podcast; episodes: Episode[] }> {
  return request("/api/feeds/import", {
    method: "POST",
    body: JSON.stringify({ rssUrl }),
  });
}

export async function updatePodcast(
  podcastId: string,
  data: Partial<Podcast>,
): Promise<Podcast> {
  return request(`/api/podcasts/${podcastId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function fetchEpisodes(
  podcastId: string,
  params: { q?: string; status?: string },
): Promise<Episode[]> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.status) search.set("status", params.status);
  const query = search.toString();
  return request(
    `/api/podcasts/${podcastId}/episodes${query ? `?${query}` : ""}`,
  );
}

export async function updateEpisode(
  podcastId: string,
  episodeId: string,
  data: Partial<Episode>,
): Promise<Episode> {
  return request(`/api/podcasts/${podcastId}/episodes/${episodeId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function publishRss(
  podcastId: string,
): Promise<{ rssUrl: string }> {
  return request(`/api/podcasts/${podcastId}/rss/publish`, {
    method: "POST",
  });
}

export async function uploadPodcastArtwork(
  podcastId: string,
  file: File,
): Promise<{ imageUrl: string }> {
  const formData = new FormData();
  formData.append("file", file);
  return formRequest(`/api/podcasts/${podcastId}/artwork`, formData);
}

export async function uploadEpisodeArtwork(
  podcastId: string,
  episodeId: string,
  file: File,
): Promise<{ imageUrl: string }> {
  const formData = new FormData();
  formData.append("file", file);
  return formRequest(
    `/api/podcasts/${podcastId}/episodes/${episodeId}/artwork`,
    formData,
  );
}

export async function uploadEpisodeAudio(
  podcastId: string,
  episodeId: string,
  file: File,
): Promise<{ audioUrl: string; audioSizeBytes: number }> {
  const formData = new FormData();
  formData.append("audioFile", file);
  return formRequest(
    `/api/podcasts/${podcastId}/episodes/${episodeId}/audio`,
    formData,
  );
}

export async function createEpisode(
  podcastId: string,
  payload: {
    title: string;
    description: string;
    status: "draft" | "published";
    audioFile: File;
  },
): Promise<Episode> {
  const formData = new FormData();
  formData.append("title", payload.title);
  formData.append("description", payload.description);
  formData.append("status", payload.status);
  formData.append("audioFile", payload.audioFile);
  return formRequest(`/api/podcasts/${podcastId}/episodes`, formData);
}
