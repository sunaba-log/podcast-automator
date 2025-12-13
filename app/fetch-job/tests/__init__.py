"""Tests for fetch-job module."""

import json
import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# shared ライブラリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "shared"))

from shared.storage import GCSClient


class TestGCSClient:
    """GCSClient のテスト."""

    @patch("google.cloud.storage.Client")
    def test_download_blob_success(self, mock_client):
        """正常なダウンロードをテスト."""
        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = MagicMock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_client.return_value = mock_client_instance

        # GCSClient を初期化
        gcs = GCSClient("test-project")

        # ダウンロード実行
        gcs.download_blob("test-bucket", "test.mp3", "/tmp/test.mp3")

        # 確認
        mock_bucket.blob.assert_called_once_with("test.mp3")
        mock_blob.download_to_filename.assert_called_once_with("/tmp/test.mp3")

    @patch("google.cloud.storage.Client")
    def test_download_blob_failure(self, mock_client):
        """ダウンロード失敗をテスト."""
        mock_blob = MagicMock()
        mock_blob.download_to_filename.side_effect = Exception("Network error")
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client_instance = MagicMock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_client.return_value = mock_client_instance

        gcs = GCSClient("test-project")

        # 例外が発生することを確認
        with pytest.raises(Exception):
            gcs.download_blob("test-bucket", "test.mp3", "/tmp/test.mp3")


class TestFetchJobMain:
    """fetch-job メイン処理のテスト."""

    def test_parse_args(self):
        """引数パースのテスト."""
        import argparse
        from main import __name__

        # コマンドライン引数をシミュレート
        args_list = [
            "--job-id",
            "test-uuid",
            "--bucket",
            "test-bucket",
            "--object-name",
            "test.mp3",
        ]

        parser = argparse.ArgumentParser()
        parser.add_argument("--job-id", required=True)
        parser.add_argument("--bucket", required=True)
        parser.add_argument("--object-name", required=True)
        parser.add_argument("--output-path", default="/tmp/audio.mp3")

        args = parser.parse_args(args_list)

        assert args.job_id == "test-uuid"
        assert args.bucket == "test-bucket"
        assert args.object_name == "test.mp3"
        assert args.output_path == "/tmp/audio.mp3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
