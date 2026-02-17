from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name)
    if value is None:
        return default or ""
    return value


@dataclass(frozen=True)
class Settings:
    r2_endpoint_url: str
    r2_bucket_name: str
    r2_access_key: str
    r2_secret_key: str
    r2_public_base_url: str
    rss_url: str
    admin_password: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        r2_endpoint_url=_get_env("R2_ENDPOINT_URL"),
        r2_bucket_name=_get_env("R2_BUCKET_NAME"),
        r2_access_key=_get_env("R2_ACCESS_KEY"),
        r2_secret_key=_get_env("R2_SECRET_KEY"),
        r2_public_base_url=_get_env("R2_PUBLIC_BASE_URL"),
        rss_url=_get_env("RSS_URL"),
        admin_password=_get_env("ADMIN_PASSWORD"),
    )
