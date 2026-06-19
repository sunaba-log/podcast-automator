from __future__ import annotations

import pytest

from entrypoints.main import _load_podcast_env


def _base_env() -> dict[str, str]:
    return {
        "PROJECT_ID": "project",
        "DATABASE_URL": "postgresql://user:password@localhost/database",
        "GCS_BUCKET": "bucket",
        "GCS_TRIGGER_OBJECT_NAME": "podcasts/1/episodes/42/source/recording.mp3",
        "R2_BUCKET": "r2",
        "CLOUDFLARE_ACCESS_KEY_ID": "access",
        "CLOUDFLARE_SECRET_ACCESS_KEY": "secret",
    }


def test_load_podcast_env_requires_database_url() -> None:
    env = _base_env()
    del env["DATABASE_URL"]

    with pytest.raises(ValueError, match="DATABASE_URL"):
        _load_podcast_env(env)


def test_load_podcast_env_does_not_require_fixed_podcast_id() -> None:
    config = _load_podcast_env(_base_env())

    assert config.database_url.startswith("postgresql://")
