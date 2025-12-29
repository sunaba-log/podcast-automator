import os
from unittest.mock import MagicMock, patch

import pytest
from services.ai_analyzer import (
    AudioAnalyzer,
    generate_transcript_with_gemini,
    summarize_transcript_with_gemini,
)


class TestAudioAnalyzerInit:
    """AudioAnalyzerの初期化テスト"""

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch("services.ai_analyzer.genai.Client")
    def test_init_with_env_vars(self, mock_client):
        """環境変数からプロジェクトIDとリージョンを取得"""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_CLOUD_PROJECT": "test-project",
                "GOOGLE_CLOUD_REGION": "asia-northeast1",
            },
        ):
            analyzer = AudioAnalyzer()

            assert analyzer.project_id == "test-project"
            assert analyzer.location == "asia-northeast1"
            mock_client.assert_called_once_with(
                vertexai=True, project="test-project", location="asia-northeast1"
            )

    @patch("services.ai_analyzer.genai.Client")
    def test_init_with_explicit_params(self, mock_client):
        """明示的なパラメータで初期化"""
        analyzer = AudioAnalyzer(project_id="my-project", location="us-west1")

        assert analyzer.project_id == "my-project"
        assert analyzer.location == "us-west1"
        mock_client.assert_called_once_with(
            vertexai=True, project="my-project", location="us-west1"
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_project_id_raises_error(self):
        """プロジェクトIDがない場合はエラーを発生"""
        with pytest.raises(
            ValueError,
            match="project_id must be provided or set in GOOGLE_CLOUD_PROJECT env var",
        ):
            AudioAnalyzer()

    @patch.dict(
        os.environ,
        {"GOOGLE_CLOUD_PROJECT": "test-project"},
        clear=True,
    )
    @patch("services.ai_analyzer.genai.Client")
    def test_init_default_location(self, mock_client):
        """デフォルトロケーションを使用"""
        analyzer = AudioAnalyzer()

        assert analyzer.location == "us-central1"


class TestGenerateTranscript:
    """generate_transcript メソッドのテスト"""

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch("services.ai_analyzer.genai.Client")
    def test_generate_transcript_success(self, mock_client_class):
        """文字起こしの生成成功"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Speaker A: Hello\nSpeaker B: Hi there"
        mock_client.models.generate_content.return_value = mock_response

        analyzer = AudioAnalyzer()
        result = analyzer.generate_transcript("gs://bucket/audio.wav")

        assert result == "Speaker A: Hello\nSpeaker B: Hi there"
        mock_client.models.generate_content.assert_called_once()

        # コール内容を確認
        call_args = mock_client.models.generate_content.call_args
        assert call_args.kwargs["model"] == "gemini-2.0-flash-001"

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch("services.ai_analyzer.genai.Client")
    def test_generate_transcript_custom_model(self, mock_client_class):
        """カスタムモデルIDで文字起こしを生成"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Transcript"
        mock_client.models.generate_content.return_value = mock_response

        analyzer = AudioAnalyzer()
        analyzer.generate_transcript("gs://bucket/audio.wav", model_id="custom-model")

        call_args = mock_client.models.generate_content.call_args
        assert call_args.kwargs["model"] == "custom-model"


class TestSummarizeTranscript:
    """summarize_transcript メソッドのテスト"""

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch("services.ai_analyzer.genai.Client")
    def test_summarize_transcript_with_custom_prompt(self, mock_client_class):
        """カスタムプロンプトで要約を生成"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Summary of the conversation"
        mock_client.models.generate_content.return_value = mock_response

        analyzer = AudioAnalyzer()
        transcript = "Long transcript here..."
        custom_prompt = "Summarize in 100 words"

        result = analyzer.summarize_transcript(transcript, custom_prompt)

        assert result == "Summary of the conversation"

        call_args = mock_client.models.generate_content.call_args
        assert custom_prompt in call_args.kwargs["contents"][0]

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch("services.ai_analyzer.genai.Client")
    def test_summarize_transcript_default_prompt(self, mock_client_class):
        """デフォルトプロンプトで要約を生成"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Summary"
        mock_client.models.generate_content.return_value = mock_response

        analyzer = AudioAnalyzer()
        transcript = "Long transcript here..."

        analyzer.summarize_transcript(transcript)

        call_args = mock_client.models.generate_content.call_args
        content = call_args.kwargs["contents"][0]
        assert "Summarize the following transcript" in content
        assert transcript in content

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch("services.ai_analyzer.genai.Client")
    def test_summarize_transcript_config(self, mock_client_class):
        """GenerateContentConfig が正しく設定される"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Summary"
        mock_client.models.generate_content.return_value = mock_response

        analyzer = AudioAnalyzer()
        analyzer.summarize_transcript("transcript")

        call_args = mock_client.models.generate_content.call_args
        config = call_args.kwargs["config"]
        assert config.temperature == 0.3
        assert config.max_output_tokens == 2000

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch("services.ai_analyzer.genai.Client")
    def test_summarize_transcript_custom_model(self, mock_client_class):
        """カスタムモデルIDで要約を生成"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Summary"
        mock_client.models.generate_content.return_value = mock_response

        analyzer = AudioAnalyzer()
        analyzer.summarize_transcript("transcript", model_id="custom-model")

        call_args = mock_client.models.generate_content.call_args
        assert call_args.kwargs["model"] == "custom-model"


class TestBackwardCompatibility:
    """後方互換性関数のテスト"""

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch("services.ai_analyzer.genai.Client")
    def test_generate_transcript_with_gemini_function(self, mock_client_class):
        """レガシー関数 generate_transcript_with_gemini が動作"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Transcript"
        mock_client.models.generate_content.return_value = mock_response

        result = generate_transcript_with_gemini("gs://bucket/audio.wav")
        assert result == "Transcript"

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"})
    @patch("services.ai_analyzer.genai.Client")
    def test_summarize_transcript_with_gemini_function(self, mock_client_class):
        """レガシー関数 summarize_transcript_with_gemini が動作"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Summary"
        mock_client.models.generate_content.return_value = mock_response

        result = summarize_transcript_with_gemini("transcript", "custom prompt")
        assert result == "Summary"
        assert result == "Summary"
