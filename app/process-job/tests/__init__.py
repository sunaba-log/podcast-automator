"""Tests for process-job module."""

import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# shared ライブラリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from shared.ai import VertexAIClient


class TestVertexAIClient:
    """VertexAIClient のテスト."""

    @patch("google.cloud.aiplatform.init")
    def test_analyze_audio_success(self, mock_init):
        """正常な音声分析をテスト."""
        ai_client = VertexAIClient(
            project_id="test-project", location="asia-northeast1", model_name="gemini-1.5-pro"
        )

        result = ai_client.analyze_audio("gs://test-bucket/test.mp3")

        assert result["status"] == "success" or "title" in result
        assert isinstance(result, dict)

    @patch("google.cloud.aiplatform.init")
    def test_process_audio_file(self, mock_init):
        """ファイル処理のテスト."""
        ai_client = VertexAIClient(
            project_id="test-project", location="asia-northeast1", model_name="gemini-1.5-pro"
        )

        result = ai_client.process_audio_file("gs://test-bucket/test.mp3")
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
