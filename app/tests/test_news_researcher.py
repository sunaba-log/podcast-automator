"""news_researcher のユニットテスト."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import DefaultCredentialsError

from services.news_researcher import (
    AINewsResearcher,
    _build_research_prompt,
    _parse_conversation_seeds,
    _resolve_credentials,
)
from services.transcript_analyzer import MentionEvidence, TopicMatch

# ── Fixtures / Helpers ─────────────────────────────────────────────────────────


def _make_topic(
    topic_id: str = "tech-ai-llm",
    display_name: str = "AI / LLM 活用",
    episode_count: int = 5,
    keywords: list[str] | None = None,
) -> TopicMatch:
    return TopicMatch(
        topic_id=topic_id,
        display_name=display_name,
        episode_count=episode_count,
        mention_count=10,
        evidence=[MentionEvidence(source_episode=1, text="AI mention", sentence_index=0)],
        keywords=keywords or ["AI", "LLM", "Gemini", "Claude"],
    )


def _make_mock_response(text: str = "Generated news content") -> MagicMock:
    """Gemini API response のモックを生成する."""
    response = MagicMock()
    response.text = text
    # grounding_metadata なし (最小ケース)
    response.candidates = []
    return response


def _make_mock_response_with_grounding(text: str = "Generated news content") -> MagicMock:
    """grounding metadata 付きの Gemini API response モック."""
    response = MagicMock()
    response.text = text
    chunk = MagicMock()
    chunk.web.title = "Test Source"
    chunk.web.uri = "https://example.com/article"
    meta = MagicMock()
    meta.grounding_chunks = [chunk]
    candidate = MagicMock()
    candidate.grounding_metadata = meta
    response.candidates = [candidate]
    return response


def _make_ai_news_text() -> str:
    return """1. **AIモデルの運用停止リスク** (出典: Example News)
・最近の論点との接続: LLMへの依存を話していたが、外部要因で突然止まる観点が加わる。
・何が面白いか: 技術選定だけではなく、供給リスクがプロダクト設計に直結する点。
・次に話せそうな問い: AI基盤を複数持つ設計はどこまで現実的か?

💬 今週の切り口: AIを前提にした開発体制の脆さから話す。
"""


# ── TestBuildResearchPrompt ────────────────────────────────────────────────────


class TestBuildResearchPrompt:
    """_build_research_prompt() のユニットテスト (pure function)."""

    def test_contains_theme_display_names(self):
        """プロンプトにテーマの表示名が含まれること."""
        themes = [_make_topic(display_name="AI / LLM 活用")]
        prompt = _build_research_prompt(themes, max_items=3)
        assert "AI / LLM 活用" in prompt

    def test_contains_episode_count(self):
        """プロンプトにエピソード数が含まれること."""
        themes = [_make_topic(episode_count=7)]
        prompt = _build_research_prompt(themes, max_items=3)
        assert "7" in prompt

    def test_contains_keywords(self):
        """プロンプトにキーワードが含まれること."""
        themes = [_make_topic(keywords=["Terraform", "GCP"])]
        prompt = _build_research_prompt(themes, max_items=3)
        assert "Terraform" in prompt
        assert "GCP" in prompt

    def test_contains_max_items(self):
        """プロンプトに max_items の値が含まれること."""
        themes = [_make_topic()]
        prompt = _build_research_prompt(themes, max_items=5)
        assert "5" in prompt

    def test_multiple_themes_all_included(self):
        """複数テーマが全てプロンプトに含まれること."""
        themes = [
            _make_topic(display_name="AI / LLM 活用"),
            _make_topic(display_name="インフラ / Terraform"),
            _make_topic(display_name="自動化 / スケジューラ"),
        ]
        prompt = _build_research_prompt(themes, max_items=3)
        assert "AI / LLM 活用" in prompt
        assert "インフラ / Terraform" in prompt
        assert "自動化 / スケジューラ" in prompt

    def test_max_5_themes_used(self):
        """6件以上あっても先頭5件のみがプロンプトに含まれること."""
        themes = [_make_topic(display_name=f"テーマ {i}") for i in range(8)]
        prompt = _build_research_prompt(themes, max_items=3)
        for i in range(5):
            assert f"テーマ {i}" in prompt
        # 6件目以降は含まれない
        assert "テーマ 5" not in prompt
        assert "テーマ 6" not in prompt

    def test_max_4_keywords_per_theme(self):
        """キーワードは先頭4件のみがプロンプトに含まれること."""
        themes = [_make_topic(keywords=["kw1", "kw2", "kw3", "kw4", "kw5", "kw6"])]
        prompt = _build_research_prompt(themes, max_items=3)
        assert "kw1" in prompt
        assert "kw4" in prompt
        assert "kw5" not in prompt
        assert "kw6" not in prompt

    def test_returns_non_empty_string(self):
        """非空文字列を返すこと."""
        themes = [_make_topic()]
        prompt = _build_research_prompt(themes, max_items=3)
        assert isinstance(prompt, str)
        assert len(prompt) > 50


# ── TestAINewsResearcher ───────────────────────────────────────────────────────


class TestAINewsResearcher:
    """AINewsResearcher のユニットテスト (Gemini クライアントをモック)."""

    @patch("services.news_researcher._resolve_credentials", return_value=None)
    @patch("services.news_researcher.genai.Client")
    def test_research_returns_response_text(self, mock_client_cls, mock_creds):
        """research() が Gemini レスポンスのテキストをそのまま返すこと."""
        _ = mock_creds
        mock_client_cls.return_value.models.generate_content.return_value = _make_mock_response(
            "## ニュース\nAI関連の最新情報"
        )
        researcher = AINewsResearcher(project_id="test-project")
        result = researcher.research([_make_topic()])
        assert result == "## ニュース\nAI関連の最新情報"

    @patch("services.news_researcher._resolve_credentials", return_value=None)
    @patch("services.news_researcher.genai.Client")
    def test_research_empty_themes_returns_empty_string(self, mock_client_cls, mock_creds):
        """テーマが空リストの場合、API を呼ばずに空文字列を返すこと."""
        _ = mock_creds
        researcher = AINewsResearcher(project_id="test-project")
        result = researcher.research([])
        assert result == ""
        mock_client_cls.return_value.models.generate_content.assert_not_called()

    @patch("services.news_researcher._resolve_credentials", return_value=None)
    @patch("services.news_researcher.genai.Client")
    def test_research_propagates_api_error(self, mock_client_cls, mock_creds):
        """Gemini API エラーが上位に伝播すること (non-fatal 制御は呼び出し元の責務)."""
        _ = mock_creds
        mock_client_cls.return_value.models.generate_content.side_effect = RuntimeError("API error")
        researcher = AINewsResearcher(project_id="test-project")
        with pytest.raises(RuntimeError, match="API error"):
            researcher.research([_make_topic()])

    @patch("services.news_researcher._resolve_credentials", return_value=None)
    @patch("services.news_researcher.genai.Client")
    def test_research_none_response_text_returns_empty_string(self, mock_client_cls, mock_creds):
        """response.text が None の場合は空文字列を返すこと."""
        _ = mock_creds
        mock_client_cls.return_value.models.generate_content.return_value = _make_mock_response(None)
        researcher = AINewsResearcher(project_id="test-project")
        result = researcher.research([_make_topic()])
        assert result == ""

    @patch("services.news_researcher._resolve_credentials", return_value=None)
    @patch("services.news_researcher.genai.Client")
    def test_research_passes_google_search_tool(self, mock_client_cls, mock_creds):
        """research() が google_search tool 付きで generate_content を呼ぶこと."""
        _ = mock_creds
        mock_client_cls.return_value.models.generate_content.return_value = _make_mock_response("output")
        researcher = AINewsResearcher(project_id="test-project")
        researcher.research([_make_topic()])

        call_kwargs = mock_client_cls.return_value.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs.args[2] if len(call_kwargs.args) > 2 else None
        if config is None:
            config = call_kwargs.kwargs.get("config")
        # tools に GoogleSearch が含まれること
        assert config is not None
        assert config.tools is not None
        assert any(hasattr(t, "google_search") and t.google_search is not None for t in config.tools)

    @patch("services.news_researcher._resolve_credentials", return_value=None)
    @patch("services.news_researcher.genai.Client")
    def test_research_with_grounding_metadata_logs_sources(self, mock_client_cls, mock_creds, caplog):
        """grounding metadata がある場合、INFO ログに sources 件数が出ること."""
        _ = mock_creds
        mock_client_cls.return_value.models.generate_content.return_value = _make_mock_response_with_grounding("output")
        researcher = AINewsResearcher(project_id="test-project")
        with caplog.at_level(logging.INFO, logger="services.news_researcher"):
            researcher.research([_make_topic()])
        assert "grounding_sources=1" in caplog.text

    @patch("services.news_researcher._resolve_credentials", return_value=None)
    @patch("services.news_researcher.genai.Client")
    def test_research_with_sources_returns_grounding_payload(self, mock_client_cls, mock_creds):
        """Grounding sourceをFirestore互換のrelated_newsへ変換すること."""
        _ = mock_creds
        mock_client_cls.return_value.models.generate_content.return_value = _make_mock_response_with_grounding("output")
        researcher = AINewsResearcher(project_id="test-project")

        result = researcher.research_with_sources([_make_topic()])

        assert result.text == "output"
        assert result.related_news == [
            {
                "title": "Test Source",
                "url": "https://example.com/article",
                "summary": "",
                "source_reason": "Gemini Google Search grounding",
            }
        ]

    def test_parse_conversation_seeds_from_ai_news_text(self):
        """AI本文から会話の種の3項目を構造化できること."""
        result = _parse_conversation_seeds(_make_ai_news_text())

        assert len(result) == 1
        assert result[0].title == "AIモデルの運用停止リスク"
        assert result[0].source == "Example News"
        assert result[0].connection == "LLMへの依存を話していたが、外部要因で突然止まる観点が加わる。"
        assert result[0].interesting == "技術選定だけではなく、供給リスクがプロダクト設計に直結する点。"
        assert result[0].question == "AI基盤を複数持つ設計はどこまで現実的か?"

    @patch("services.news_researcher._resolve_credentials", return_value=None)
    @patch("services.news_researcher.genai.Client")
    def test_research_with_sources_merges_ai_angles_into_related_news(self, mock_client_cls, mock_creds):
        """AI本文の3項目をFirestore保存用related_newsへ反映すること."""
        _ = mock_creds
        mock_client_cls.return_value.models.generate_content.return_value = _make_mock_response_with_grounding(
            _make_ai_news_text()
        )
        researcher = AINewsResearcher(project_id="test-project")

        result = researcher.research_with_sources([_make_topic()])

        assert result.related_news == [
            {
                "title": "AIモデルの運用停止リスク",
                "url": "https://example.com/article",
                "summary": "技術選定だけではなく、供給リスクがプロダクト設計に直結する点。",
                "source": "Example News",
                "source_reason": "LLMへの依存を話していたが、外部要因で突然止まる観点が加わる。",
                "question": "AI基盤を複数持つ設計はどこまで現実的か?",
            }
        ]

    @patch("services.news_researcher._resolve_credentials", return_value=None)
    @patch("services.news_researcher.genai.Client")
    def test_research_uses_configured_model(self, mock_client_cls, mock_creds):
        """指定したモデル ID が generate_content に渡されること."""
        _ = mock_creds
        mock_client_cls.return_value.models.generate_content.return_value = _make_mock_response("output")
        researcher = AINewsResearcher(project_id="test-project", model="gemini-2.5-pro")
        researcher.research([_make_topic()])

        call_args = mock_client_cls.return_value.models.generate_content.call_args
        model_arg = call_args.kwargs.get("model") or call_args.args[0]
        assert model_arg == "gemini-2.5-pro"

    @patch("services.news_researcher._resolve_credentials", return_value=None)
    @patch("services.news_researcher.genai.Client")
    def test_researcher_initializes_with_vertexai(self, mock_client_cls, mock_creds):
        """AINewsResearcher が vertexai=True で Client を初期化すること."""
        _ = mock_creds
        AINewsResearcher(project_id="my-project")
        call_kwargs = mock_client_cls.call_args.kwargs
        assert call_kwargs.get("vertexai") is True
        assert call_kwargs.get("project") == "my-project"


# ── TestResolveCredentials ─────────────────────────────────────────────────────


class TestResolveCredentials:
    """_resolve_credentials() のユニットテスト."""

    @patch("services.news_researcher.subprocess.run")
    @patch("services.news_researcher.genai")
    def test_returns_none_when_both_fail(self, mock_genai, mock_subprocess):
        """ADC も gcloud token も使えない場合 None を返すこと."""
        _ = mock_genai
        # ADC 失敗は google.auth.default のパッチで制御
        mock_subprocess.side_effect = FileNotFoundError("gcloud not found")
        with patch("google.auth.default", side_effect=DefaultCredentialsError("No ADC")):
            result = _resolve_credentials()
        assert result is None

    @patch("services.news_researcher.subprocess.run")
    def test_returns_credentials_from_gcloud_token(self, mock_subprocess):
        """gcloud token が取得できる場合、Credentials を返すこと."""
        mock_subprocess.return_value = MagicMock(stdout="fake-token-12345")
        with (
            patch("services.news_researcher.shutil.which", return_value="/usr/bin/gcloud"),
            patch("google.auth.default", side_effect=DefaultCredentialsError("No ADC")),
        ):
            result = _resolve_credentials()
        # token が設定された Credentials オブジェクトであること
        assert result is not None
        assert result.token == "fake-token-12345"
