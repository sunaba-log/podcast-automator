from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient


def _client() -> TestClient:
    os.environ["ADMIN_PASSWORD"] = "testpass"
    os.environ["R2_PUBLIC_BASE_URL"] = "http://localhost:9000"
    from src.config import get_settings

    get_settings.cache_clear()
    from src.main import app

    return TestClient(app)


def test_media_upload_and_create_episode() -> None:
    client = _client()
    root = Path(__file__).resolve().parents[2]
    rss_path = root / "app" / "data" / "rss_feed.xml"
    rss_url = rss_path.as_uri()

    response = client.post(
        "/api/feeds/import",
        json={"rssUrl": rss_url},
        headers={"X-Admin-Password": "testpass"},
    )
    payload = response.json()
    podcast_id = payload["podcast"]["id"]
    episode_id = payload["episodes"][0]["id"]

    image_response = client.post(
        f"/api/podcasts/{podcast_id}/artwork",
        files={"file": ("cover.jpg", b"image", "image/jpeg")},
        headers={"X-Admin-Password": "testpass"},
    )
    assert image_response.status_code == 200
    assert image_response.json()["imageUrl"].startswith("http")

    episode_image_response = client.post(
        f"/api/podcasts/{podcast_id}/episodes/{episode_id}/artwork",
        files={"file": ("episode.jpg", b"image", "image/jpeg")},
        headers={"X-Admin-Password": "testpass"},
    )
    assert episode_image_response.status_code == 200

    audio_response = client.post(
        f"/api/podcasts/{podcast_id}/episodes/{episode_id}/audio",
        files={"audioFile": ("audio.mp3", b"audio", "audio/mpeg")},
        headers={"X-Admin-Password": "testpass"},
    )
    assert audio_response.status_code == 200
    assert audio_response.json()["audioSizeBytes"] == 5

    create_response = client.post(
        f"/api/podcasts/{podcast_id}/episodes",
        data={"title": "New Episode", "description": "New desc", "status": "draft"},
        files={"audioFile": ("new.mp3", b"audio", "audio/mpeg")},
        headers={"X-Admin-Password": "testpass"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == "New Episode"
