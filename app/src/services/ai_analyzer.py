import os  # noqa: D100
from pathlib import Path

from google import genai
from google.genai.types import GenerateContentConfig, Part
from pydantic import BaseModel, Field

# 参考 https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/use-cases/multimodal-sentiment-analysis/intro_to_multimodal_sentiment_analysis.ipynb

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


# 構造化出力用モデル
# https://ai.google.dev/gemini-api/docs/structured-output?hl=ja&example=recipe
class Summary(BaseModel):
    """音声要約の構造化出力モデル."""

    title: str = Field(..., description="会議の見出し")
    description: str = Field(..., description="会議内容の説明文")


class AudioAnalyzer:
    """Gemini APIを使った音声分析クラス.

    音声ファイルの文字起こしと要約を生成する機能を提供。

    Args:
        project_id: GCPプロジェクトID. 指定しない場合は環境変数から取得.
        location: リージョン. デフォルトは us-central1.

    Raises:
        ValueError: project_idが指定されていない場合.

    Methods:
        generate_transcript(gcs_uri, model_id): 音声ファイルの文字起こしを生成.
        summarize_transcript(transcript, prompt, model_id): 文字起こしの要約を生成.
    """

    DEFAULT_MODEL_ID = "gemini-2.0-flash-001"
    DEFAULT_LOCATION = "us-central1"

    def __init__(self, project_id: str | None = None, location: str | None = None) -> None:
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
            msg = f"Unsupported audio format: .{extension}. Supported formats: {supported}"
            raise ValueError(msg)

        return AUDIO_FORMAT_MAPPING[extension]

    def generate_transcript(self, gcs_uri: str, model_id: str | None = None) -> str | None:
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
        prompt = "提供されたポッドキャスト配信の音声記録をもとに、議事録を作成して下さい。議論された主要なトピック、決定事項、各担当者のアクションアイテムを正確かつ簡潔に記録した、フォーマルなビジネス文書にして下さい。登場人物は小野、数森、高島です。"

        response = self.client.models.generate_content(
            model=model_id,
            contents=[audio_part, prompt],
        )

        return response.text

    def summarize_transcript(self, transcript: str, prompt: str | None = None, model_id: str | None = None) -> Summary:
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
            prompt = f"""
以下はポッドキャストの議事録です。
この内容をもとに、リスナーの興味を引く形で番組紹介文を作成してください。

要件:
- 日本語で出力すること
- 全体はポッドキャスト配信用の文章とする
- 以下の構成・形式を必ず守ること

【出力フォーマット】

【エピソードタイトル】
(キャッチーで分かりやすいタイトル、200文字以内)

【番組紹介】
sunaba log: 友人同士で週次で雑談しながら「30 days to build」プロジェクトを進行する、雑談発想型プロトタイピング会議録。

【目次】
(議事録の内容から主要トピックを時系列で抽出し、以下の形式で記載)
0:00 AAA
0:16 BBB
5:00 CCC
12:54 DDD
17:11 EEE

【概要】
全体内容を400字程度で要約してください。

【関連情報】
- sunabalog GitHubリポジトリ: https://github.com/sunaba-log/podcast-automator.git
- 技術スタック: 今回扱われた技術スタックを箇条書きで列挙
- キーワード: 今回扱われたキーワードを箇条書きで列挙

--- 以下が議事録です ---
{transcript}
"""

        response = self.client.models.generate_content(
            model=model_id,
            contents=[prompt],
            config=GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2000,
                response_mime_type="application/json",
                response_json_schema=Summary.model_json_schema(),
            ),
        )
        if not response.text:
            raise ValueError("No response received from the model.")
        return Summary.model_validate_json(response.text)


# 後方互換性のための関数ラッパー
def generate_transcript_with_gemini(gcs_uri: str) -> str | None:
    """Geminiモデルを使って音声ファイルの文字起こしを生成.

    Deprecated: AudioAnalyzer.generate_transcript() を使用してください.
    """
    analyzer = AudioAnalyzer()
    if not gcs_uri:
        raise ValueError("gcs_uri must be provided.")
    return analyzer.generate_transcript(gcs_uri)


def summarize_transcript_with_gemini(
    transcript: str, prompt: str | None = None, model_id: str = "gemini-2.0-flash-001"
) -> Summary:
    """Geminiモデルを使って文字起こしの要約を生成.

    Deprecated: AudioAnalyzer.summarize_transcript() を使用してください.
    """
    analyzer = AudioAnalyzer()
    return analyzer.summarize_transcript(transcript, prompt, model_id)
