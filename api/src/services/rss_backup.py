from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.config import get_settings
from src.schemas.rss import RssBackup

BACKUP_DIR = Path(".data/backups")


def create_backup(rss_url: str, raw_xml: str) -> RssBackup:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    filename = f"{backup_id}.xml"
    backup_path = BACKUP_DIR / filename
    backup_path.write_text(raw_xml, encoding="utf-8")
    settings = get_settings()
    base_url = settings.r2_public_base_url.rstrip("/")
    backup_url = f"{base_url}/backups/{filename}" if base_url else str(backup_path)
    created_at = datetime.now(timezone.utc).isoformat()
    return RssBackup(id=backup_id, rssUrl=rss_url, backupUrl=backup_url, createdAt=created_at)
