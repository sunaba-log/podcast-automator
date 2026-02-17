from __future__ import annotations

from pydantic import BaseModel


class RssBackup(BaseModel):
    id: str
    rssUrl: str
    backupUrl: str
    createdAt: str


class PublishResult(BaseModel):
    rssUrl: str
    backup: RssBackup
