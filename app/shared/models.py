"""Shared data models."""

from dataclasses import dataclass, asdict
from typing import Optional
import json


@dataclass
class PodcastProcessingJob:
    """Podcast処理ジョブの状態を表すデータモデル."""

    job_id: str  # UUID
    input_bucket: str
    input_object: str  # GCS object name (mp3 file)
    status: str  # "queued" | "fetch_in_progress" | "process_in_progress" | "upload_in_progress" | "completed" | "failed"
    metadata: Optional[dict] = None  # {title, summary, transcript}
    output_url: Optional[str] = None  # R2 URL
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> "PodcastProcessingJob":
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class ProcessingMetadata:
    """Vertex AI からの処理結果メタデータ."""

    title: str
    summary: str
    transcript: str
    duration_seconds: Optional[int] = None
    keywords: Optional[list] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))
