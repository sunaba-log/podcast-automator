"""Gemini-based audio analysis and summary generation."""

import logging
import os
from pathlib import Path

from google import genai
from google.genai.types import GenerateContentConfig, Part

from domain.interfaces import TranscriptProvider
from domain.models import SnsPromotionsResponse, Summary

logger = logging.getLogger(__name__)

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


class AudioAnalyzer(TranscriptProvider):
    """Gemini API based audio analysis."""

    DEFAULT_MODEL_ID = "gemini-2.0-flash-001"
    DEFAULT_LOCATION = "us-central1"

    def __init__(self, project_id: str | None = None, location: str | None = None) -> None:
        """Initialize analyzer with project and location settings."""
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("project_id must be provided or set in GOOGLE_CLOUD_PROJECT env var")
        self.location = location or os.environ.get("GOOGLE_CLOUD_REGION", self.DEFAULT_LOCATION)
        self.client = genai.Client(vertexai=True, project=self.project_id, location=self.location)

    @staticmethod
    def _get_mime_type(gcs_uri: str) -> str:
        file_path = Path(gcs_uri)
        extension = file_path.suffix.lstrip(".").lower()

        if extension not in AUDIO_FORMAT_MAPPING:
            supported = ", ".join(sorted(AUDIO_FORMAT_MAPPING.keys()))
            msg = f"Unsupported audio format: .{extension}. Supported formats: {supported}"
            raise ValueError(msg)

        return AUDIO_FORMAT_MAPPING[extension]

    def generate_transcript(self, gcs_uri: str, model_id: str | None = None) -> str | None:
        """Generate transcript text from an audio object in GCS."""
        model_id = model_id or self.DEFAULT_MODEL_ID
        mime_type = self._get_mime_type(gcs_uri)

        audio_part = Part.from_uri(
            file_uri=gcs_uri,
            mime_type=mime_type,
        )
        prompt = """
提供されたポッドキャスト配信の音声記録をもとに、議事録を作成して下さい。
議論された主要なトピック、決定事項、各担当者のアクションアイテムを正確かつ簡潔に記録した、フォーマルなビジネス文書にして下さい。
また、【目次】も作成して下さい。(議事録の内容から主要トピックを時系列で抽出し、以下の形式で記載)
0:00 AAA
0:16 BBB
5:00 CCC
12:54 DDD
17:11 EEE
登場人物は小野、数森、高島です。
"""

        response = self.client.models.generate_content(
            model=model_id,
            contents=[audio_part, prompt],
        )

        return response.text

    def summarize_transcript(self, transcript: str, prompt: str | None = None, model_id: str | None = None) -> Summary:
        """Generate a structured summary from transcript text."""
        model_id = model_id or self.DEFAULT_MODEL_ID

        if not prompt:
            prompt = f"""
以下の議事録の内容をもとに、リスナーの興味を引く形で番組紹介文を作成してください。

出力は必ず **JSONのみ** とし、次のスキーマに厳密に従ってください。
{{
    "title": "キャッチーで分かりやすいエピソードタイトル(200文字以内)",
    "description": "RSSフィードに適した番組紹介文。HTMLタグは<p>と<br>のみを使用してください。段落は<p>...</p>で囲み、改行は<br>を使用してください。その他のHTMLタグは使用しないでください。"
}}

制約条件:
- descriptionには、以下の見出しを必ず含めること
  1. エピソード概要(400字程度の概要)
  2. 目次
  3. 関連情報
    技術スタックとキーワードは**箇条書き**で列挙すること
    キーワード: 議事録内で扱われたキーワードを**箇条書き**で列挙
  4. about us
- HTMLタグは<p>と<br>のみを使用すること
- 見出しは【】で囲んでテキストとして表現すること

descriptionの出力例:
<p>【エピソード概要】</p><p><br></p><p>【目次】</p><p>0:00 AAA</p><p>0:16 BBB</p><p><br></p><p>【関連情報】</p><p>- GitHub: https://github.com/sunaba-log</p><p>- 技術スタック: 議事録内で扱われた技術スタックを箇条書きで列挙</p><p>  - 例: GCS</p><p>- キーワード: 議事録内で扱われたキーワードを箇条書きで列挙</p><p>  - 例: ARグラス</p><p><br></p><p>【about us】</p><p>sunaba log: 友人同士で週次で雑談しながら「30 days to build」プロジェクトを進行する、雑談発想型プロトタイピング会議録。</p>

--- 以下が議事録です ---
{transcript}
"""

        response = self.client.models.generate_content(
            model=model_id,
            contents=[prompt],
            config=GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=12000,
                response_mime_type="application/json",
                response_json_schema=Summary.model_json_schema(),
            ),
        )
        if not response.text:
            raise ValueError("No response received from the model.")

        text = response.text.strip()
        if not text.endswith("}"):
            logger.error("Model output truncated or incomplete JSON. response.text=%s", text)
            raise ValueError(
                "Model output was truncated or incomplete JSON. Try increasing max_output_tokens or simplifying the prompt."
            )

        try:
            return Summary.model_validate_json(text)
        except Exception as err:
            logger.warning("Summary JSON validation failed. response.text=%s", text)
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = text[start : end + 1]
                if not candidate.endswith("}"):
                    logger.exception("Recovered JSON is still incomplete. candidate=%s", candidate)
                    raise ValueError(
                        "Recovered JSON is still incomplete. Try increasing max_output_tokens or simplifying the prompt."
                    ) from err
                return Summary.model_validate_json(candidate)
            raise

    def generate_sns_promotions(
        self,
        summary_description: str,
        num_promotions: int = 3,
        model_id: str | None = None,
    ) -> SnsPromotionsResponse:
        """Generate multiple SNS promotions from episode summary description using Gemini."""
        model_id = model_id or self.DEFAULT_MODEL_ID

        prompt = f"""
以下のポッドキャストのエピソード紹介文をもとに、SNS投稿文を {num_promotions} 種類作成してください。

各投稿は、切り口の異なるパターン(例: 告知重視、インサイト重視、パワーワード重視など)にしてください。

制約事項:
- 読み手が思わずクリックしたくなるような、簡潔で魅力的な言葉を選んでください。
- ハッシュタグは文脈に合わせて3個程度選定してください。
- ややフレンドリーな口調で。

出力は必ず **JSONのみ** とし、次のスキーマに厳密に従ってください。
スキーマ:
{{
    "promotions": [
        {{
            "message": "SNS投稿文の本文",
            "hashtags": ["#タグ1", "#タグ2", "#タグ3"]
        }},
        ...
    ]
}}

--- 以下がエピソード紹介文です ---
{summary_description}
"""

        response = self.client.models.generate_content(
            model=model_id,
            contents=[prompt],
            config=GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=4000,
                response_mime_type="application/json",
                response_json_schema=SnsPromotionsResponse.model_json_schema(),
            ),
        )
        if not response.text:
            raise ValueError("No response received from the model for SNS promotion.")

        text = response.text.strip()
        try:
            return SnsPromotionsResponse.model_validate_json(text)
        except Exception as err:
            logger.warning("SNS Promotion JSON validation failed. response.text=%s", text)
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = text[start : end + 1]
                return SnsPromotionsResponse.model_validate_json(candidate)
            raise



def generate_transcript_with_gemini(gcs_uri: str) -> str | None:
    """Deprecated helper wrapper."""
    analyzer = AudioAnalyzer()
    if not gcs_uri:
        raise ValueError("gcs_uri must be provided.")
    return analyzer.generate_transcript(gcs_uri)


def summarize_transcript_with_gemini(
    transcript: str, prompt: str | None = None, model_id: str = "gemini-2.0-flash-001"
) -> Summary:
    """Deprecated helper wrapper."""
    analyzer = AudioAnalyzer()
    return analyzer.summarize_transcript(transcript, prompt, model_id)
