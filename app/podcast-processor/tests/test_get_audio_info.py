"""
Usage:
python -m pytest tests/test_get_audio_info.py -v
"""

import io
import sys
from pathlib import Path

from services import get_audio_info

# 親ディレクトリのservicesモジュールをインポート
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestGetAudioInfo:
    """オーディオ情報取得機能のテストクラス"""

    def test_get_audio_info(self):
        """オーディオ情報を取得する"""
        # TODO: 実装
        with io.BytesIO() as file_buffer:
            with open("./data/short_dialogue.m4a", "rb") as f:
                file_buffer.write(f.read())
            file_buffer.seek(0)
            result = get_audio_info(file_buffer=file_buffer, audio_format="m4a")
            assert len(result) == 2
            assert isinstance(result[0], int)
            assert isinstance(result[1], str)
            assert result[0] > 0  # ファイルサイズが正の整数であることを確認
            assert result[1].count(":") == 2  # durationがHH:MM:SS形式であることを確認
            print(f"File size: {result[0]} bytes, Duration: {result[1]}")
