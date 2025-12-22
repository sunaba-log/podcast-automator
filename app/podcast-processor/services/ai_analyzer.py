import os

from google import genai
from google.cloud import aiplatform
from google.genai.types import Content, GenerateContentConfig, Part

# 参考：https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/use-cases/multimodal-sentiment-analysis/intro_to_multimodal_sentiment_analysis.ipynb


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

    def generate_transcript(self, gcs_uri: str, model_id: str | None = None) -> str:
        """Geminiモデルを使って音声ファイルの文字起こしを生成.

        Args:
            gcs_uri: GCS上の音声ファイルのURI.
            model_id: 使用するモデルID. デフォルトは gemini-2.0-flash-001.

        Returns:
            生成された文字起こしテキスト.
        """
        model_id = model_id or self.DEFAULT_MODEL_ID

        audio_part = Part.from_uri(
            file_uri=gcs_uri,
            mime_type="audio/x-m4a",
        )
        prompt = "Generate a transcript of this conversation. Use speaker A, speaker B, etc to identify speakers."

        response = self.client.models.generate_content(
            model=model_id,
            contents=[
                audio_part,
                prompt,
            ],
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
