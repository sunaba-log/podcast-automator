import os
from pathlib import Path

from google import genai
from google.genai.types import GenerateContentConfig, Part

# 参考：https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/use-cases/multimodal-sentiment-analysis/intro_to_multimodal_sentiment_analysis.ipynb

# Gemini対応の音声フォーマットマッピング
AUDIO_FORMAT_MAPPING = {
    "aac": "audio/aac",
    "aiff": "audio/aiff",
    "flac": "audio/flac",
    "m4a": "audio/m4a",
    "mp3": "audio/mp3",
    "mp4": "audio/mp4",
    "mpeg": "audio/mpeg",
    "mpga": "audio/mpga",
    "ogg": "audio/ogg",
    "opus": "audio/opus",
    "pcm": "audio/pcm",
    "wav": "audio/wav",
    "webm": "audio/webm",
}


class AudioAnalyzer:
    """Gemini APIを使った音声分析クラス."""

    DEFAULT_MODEL_ID = "gemini-2.0-flash-001"
    DEFAULT_LOCATION = "us-central1"

    def __init__(self, project_id: str | None = None, location: str | None = None):
        """AudioAnalyzerを初期化.

        Args:
            project_id: GCPプロジェクトID. 指定しない場合は環境変数から取得.
            location: リージョン. デフォルトは us-central1.
        """
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("project_id must be provided or set in GOOGLE_CLOUD_PROJECT env var")
        self.location = location or os.environ.get("GOOGLE_CLOUD_REGION", self.DEFAULT_LOCATION)
        self.client = genai.Client(vertexai=True, project=self.project_id, location=self.location)

    @staticmethod
    def _get_mime_type(gcs_uri: str) -> str:
        """URIから拡張子を取得し、対応するMIMEタイプを返す.

        Args:
            gcs_uri: GCS上のファイルのURI (例: gs://bucket/audio.m4a).

        Returns:
            MIMEタイプ文字列.

        Raises:
            ValueError: 対応していない拡張子の場合.
        """
        file_path = Path(gcs_uri)
        extension = file_path.suffix.lstrip(".").lower()

        if extension not in AUDIO_FORMAT_MAPPING:
            supported = ", ".join(sorted(AUDIO_FORMAT_MAPPING.keys()))
            raise ValueError(
                f"Unsupported audio format: .{extension}. Supported formats: {supported}"
            )

        return AUDIO_FORMAT_MAPPING[extension]

    def generate_transcript(self, gcs_uri: str, model_id: str | None = None) -> str:
        """Geminiモデルを使って音声ファイルの文字起こしを生成.

        Args:
            gcs_uri: GCS上の音声ファイルのURI (例: gs://bucket/audio.m4a).
            model_id: 使用するモデルID. デフォルトは gemini-2.0-flash-001.

        Returns:
            生成された文字起こしテキスト.

        Raises:
            ValueError: 対応していない音声フォーマットの場合.
        """
        model_id = model_id or self.DEFAULT_MODEL_ID

        # URIから拡張子を取得してMIMEタイプを決定
        mime_type = self._get_mime_type(gcs_uri)

        audio_part = Part.from_uri(
            file_uri=gcs_uri,
            mime_type=mime_type,
        )
        prompt = "Generate a transcript of this conversation. Use speaker A, speaker B, etc to identify speakers."

        response = self.client.models.generate_content(
            model=model_id,
            contents=[audio_part, prompt],
        )

        return response.text

    def summarize_transcript(
        self, transcript: str, prompt: str = "", model_id: str | None = None
    ) -> str:
        """Geminiモデルを使って文字起こしの要約を生成.

        Args:
            transcript: 文字起こしテキスト.
            prompt: カスタムプロンプト. 指定しない場合はデフォルトプロンプトを使用.
            model_id: 使用するモデルID. デフォルトは gemini-2.0-flash-001.

        Returns:
            生成された要約テキスト.
        """
        model_id = model_id or self.DEFAULT_MODEL_ID

        if not prompt:
            prompt = f"Summarize the following transcript in a concise manner:\n\n{transcript}"

        response = self.client.models.generate_content(
            model=model_id,
            contents=[prompt],
            config=GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2000,
            ),
        )
        return response.text


# 後方互換性のための関数ラッパー
def generate_transcript_with_gemini(gcs_uri: str) -> str:
    """Geminiモデルを使って音声ファイルの文字起こしを生成.

    Deprecated: AudioAnalyzer.generate_transcript() を使用してください.
    """
    analyzer = AudioAnalyzer()
    return analyzer.generate_transcript(gcs_uri)


def summarize_transcript_with_gemini(
    transcript: str, prompt: str, model_id: str = "gemini-2.0-flash-001"
) -> str:
    """Geminiモデルを使って文字起こしの要約を生成.

    Deprecated: AudioAnalyzer.summarize_transcript() を使用してください.
    """
    analyzer = AudioAnalyzer()
    return analyzer.summarize_transcript(transcript, prompt, model_id)
