from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_rss_import_update_publish() -> None:
    os.environ["ADMIN_PASSWORD"] = "testpass"
    from src.config import get_settings

    get_settings.cache_clear()
    from src.main import app

    client = TestClient(app)
    root = Path(__file__).resolve().parents[2]
    rss_path = root / "app" / "data" / "rss_feed.xml"
    rss_url = rss_path.as_uri()

    response = client.post(
        "/api/feeds/import",
        json={"rssUrl": rss_url},
        headers={"X-Admin-Password": "testpass"},
    )
    assert response.status_code == 200
    payload = response.json()
    podcast_id = payload["podcast"]["id"]
    episode_id = payload["episodes"][0]["id"]

    update_response = client.patch(
        f"/api/podcasts/{podcast_id}",
        json={"title": "Updated Title"},
        headers={"X-Admin-Password": "testpass"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Title"

    episode_response = client.patch(
        f"/api/podcasts/{podcast_id}/episodes/{episode_id}",
        json={"title": "Updated Episode"},
        headers={"X-Admin-Password": "testpass"},
    )
    assert episode_response.status_code == 200
    assert episode_response.json()["title"] == "Updated Episode"

    publish_response = client.post(
        f"/api/podcasts/{podcast_id}/rss/publish",
        headers={"X-Admin-Password": "testpass"},
    )
    assert publish_response.status_code == 200
    publish_payload = publish_response.json()
    assert publish_payload["rssUrl"]
    assert publish_payload["backup"]["backupUrl"]
