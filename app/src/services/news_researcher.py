"""Gemini Google Search grounding を使った AI-driven ニュース調査サービス.

設計方針:
- Pure logic は _build_research_prompt() に閉じ込める
- I/O (Gemini API 呼び出し) は AINewsResearcher.research() のみ
- Auth: ADC → gcloud token の順で解決 (Cloud Run / ローカル両対応)
- 失敗は例外として上位に伝播させる (non-fatal 制御は呼び出し元の責務)
- RSS pipeline の代替。fallback は呼び出し元 (agenda_main.py) が管理する
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

import google.auth
from google import genai
from google.auth.exceptions import DefaultCredentialsError
from google.genai import types
from google.oauth2 import credentials as google_oauth2_credentials

if TYPE_CHECKING:
    from services.transcript_analyzer import TopicMatch

logger = logging.getLogger(__name__)

_DEFAULT_MODEL: str = "gemini-2.5-flash"
_DEFAULT_LOCATION: str = "us-central1"
_DEFAULT_MAX_ITEMS: int = 3
_NEWS_ITEM_RE = re.compile(
    r"^\s*\d+\.\s+\*\*(?P<title>.+?)\*\*\s+\(出典:\s*(?P<source>.+?)\)\s*$",
)
_CONNECTION_PREFIX = "・最近の論点との接続:"
_INTERESTING_PREFIX = "・何が面白いか:"
_QUESTION_PREFIX = "・次に話せそうな問い:"


@dataclass(frozen=True)
class AIConversationSeed:
    """Structured conversation seed parsed from the AI news markdown."""

    title: str
    source: str
    connection: str
    interesting: str
    question: str


@dataclass(frozen=True)
class AINewsResearchResult:
    """AI news text and grounding sources for downstream persistence."""

    text: str
    related_news: list[dict[str, str]]


class AINewsResearcher:
    """Gemini Google Search grounding によるニュース調査クラス.

    transcript の recurring_themes を受け取り、直近1週間の関連ニュースと
    会話の種を生成して Discord markdown テキストとして返す。

    Args:
        project_id: GCP プロジェクト ID。
        location: Vertex AI のリージョン。デフォルト us-central1。
        model: 使用する Gemini モデル ID。
        credentials: 認証情報。None の場合は _resolve_credentials() で自動解決。
    """

    def __init__(
        self,
        project_id: str,
        location: str = _DEFAULT_LOCATION,
        model: str = _DEFAULT_MODEL,
        credentials: object | None = None,
    ) -> None:
        """Initialize the Gemini client with resolved credentials.

        Args:
            project_id: GCP プロジェクト ID。
            location: Vertex AI のリージョン。
            model: 使用する Gemini モデル ID。
            credentials: 明示的な認証情報。None の場合は自動解決する。
        """
        self._model = model
        resolved = credentials if credentials is not None else _resolve_credentials()
        self._client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            **({"credentials": resolved} if resolved is not None else {}),
        )

    def research(
        self,
        recurring_themes: list[TopicMatch],
        *,
        max_items: int = _DEFAULT_MAX_ITEMS,
    ) -> str:
        """Transcript テーマを基に直近ニュースを調査して Discord 向け markdown を返す.

        Args:
            recurring_themes: AgendaResult.recurring_themes のリスト。
            max_items: 取得するニュース件数の目安 (Gemini へのヒント)。

        Returns:
            Discord markdown 形式の文字列。空のテーマリストの場合は空文字列。

        Raises:
            google.api_core.exceptions.GoogleAPIError: Gemini API 呼び出し失敗時。
        """
        return self.research_with_sources(recurring_themes, max_items=max_items).text

    def research_with_sources(
        self,
        recurring_themes: list[TopicMatch],
        *,
        max_items: int = _DEFAULT_MAX_ITEMS,
    ) -> AINewsResearchResult:
        """Research news and return Discord text with grounding sources."""
        if not recurring_themes:
            logger.info("news_researcher: no themes, skipping research")
            return AINewsResearchResult(text="", related_news=[])

        prompt = _build_research_prompt(recurring_themes, max_items)
        logger.info(
            "news_researcher: starting research (themes=%d, max_items=%d)",
            len(recurring_themes),
            max_items,
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.4,
            ),
        )

        result_text: str = response.text or ""
        related_news: list[dict[str, str]] = []

        # grounding sources をデバッグログに出す (observability)
        if response.candidates and response.candidates[0].grounding_metadata:
            meta = response.candidates[0].grounding_metadata
            chunks = meta.grounding_chunks or []
            logger.info(
                "news_researcher: generated %d chars, grounding_sources=%d",
                len(result_text),
                len(chunks),
            )
            seen_urls: set[str] = set()
            for chunk in chunks:
                if chunk.web:
                    logger.debug("  grounding: %s", chunk.web.title or chunk.web.uri)
                    url = str(chunk.web.uri or "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    related_news.append(
                        {
                            "title": str(chunk.web.title or url),
                            "url": url,
                            "summary": "",
                            "source_reason": "Gemini Google Search grounding",
                        }
                    )
                    if len(related_news) >= max_items:
                        break
        else:
            logger.info("news_researcher: generated %d chars (no grounding metadata)", len(result_text))

        conversation_seeds = _parse_conversation_seeds(result_text)
        if conversation_seeds:
            related_news = _merge_conversation_seeds_into_related_news(
                conversation_seeds=conversation_seeds,
                related_news=related_news,
                max_items=max_items,
            )

        return AINewsResearchResult(text=result_text, related_news=related_news)


# ── Prompt builder ─────────────────────────────────────────────────────────────


def _build_research_prompt(
    themes: list[TopicMatch],
    max_items: int,
) -> str:
    """Research prompt を構築する.

    Args:
        themes: 調査対象のテーマリスト。先頭 5 件を使用する。
        max_items: 取得するニュース件数の目安。

    Returns:
        Gemini に渡す prompt 文字列。
    """
    themes_text = "\n".join(
        f"- {t.display_name} (直近 {t.episode_count} 回の収録で繰り返し登場、キーワード: {' / '.join(t.keywords[:4])})"
        for t in themes[:5]
    )

    return f"""sunabalog (エンジニア系ポッドキャスト) で直近繰り返し話題になっているテーマ:

{themes_text}

上記テーマの文脈から、直近1週間のニュース・技術動向を調査してください。
「次の収録で話したくなる話題」を **強い順に 1〜{max_items} 件**だけ選んでください。
3件揃えるために質の低い話題を入れないこと。強い話題が2件なら2件で止める。

選ぶ基準 (優先順):
1. surprising connection — 予想外の角度でテーマとつながる、「そうきたか」という発見
2. contradiction / tension — 最近の議論を揺さぶる逆説・「それって逆に価値下がる?」
3. 「人間の役割どう変わる?」「これが当たり前になったら?」的な問いが生まれる
4. テーマとの具体的な接点がある (「今週のAIニュースまとめ」的な汎用情報は避ける)

前置き・挨拶・まとめ文は不要。以下の形式のみで出力してください:

1. **ニュースタイトル** (出典: メディア名またはURL)
・最近の論点との接続: (1文。テーマ名の説明ではなく「〜という問いがあったが」「〜を話していたが逆に」の形で)
・何が面白いか: (1文。意外性・逆説・驚き・人間の役割の変化など)
・次に話せそうな問い: (1文)

(最大{max_items}件。強い話題のみ)

💬 今週の切り口: (1文。今週どこから話すか)

制約:
- 1件あたり4行以内
- 不確かな情報は「〜とのこと」等で断定を避ける
"""


# ── Response parsing ───────────────────────────────────────────────────────────


def _parse_conversation_seeds(text: str) -> list[AIConversationSeed]:
    """Parse the fixed AI news markdown format into structured conversation seeds."""
    seeds: list[AIConversationSeed] = []
    current: dict[str, str] | None = None

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        required = ("title", "source", "connection", "interesting", "question")
        if all(current.get(key) for key in required):
            seeds.append(
                AIConversationSeed(
                    title=current["title"],
                    source=current["source"],
                    connection=current["connection"],
                    interesting=current["interesting"],
                    question=current["question"],
                )
            )
        current = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = _NEWS_ITEM_RE.match(line)
        if match:
            flush()
            current = {
                "title": match.group("title").strip(),
                "source": match.group("source").strip(),
            }
            continue

        if current is None:
            continue

        if line.startswith(_CONNECTION_PREFIX):
            current["connection"] = line.removeprefix(_CONNECTION_PREFIX).strip()
        elif line.startswith(_INTERESTING_PREFIX):
            current["interesting"] = line.removeprefix(_INTERESTING_PREFIX).strip()
        elif line.startswith(_QUESTION_PREFIX):
            current["question"] = line.removeprefix(_QUESTION_PREFIX).strip()

    flush()
    return seeds


def _merge_conversation_seeds_into_related_news(
    *,
    conversation_seeds: list[AIConversationSeed],
    related_news: list[dict[str, str]],
    max_items: int,
) -> list[dict[str, str]]:
    """Attach AI-generated discussion angles to Firestore related_news payloads."""
    merged = [dict(item) for item in related_news[:max_items]]

    for index, seed in enumerate(conversation_seeds[:max_items]):
        if index < len(merged):
            item = merged[index]
        else:
            item = {"url": ""}
            merged.append(item)

        item.update(
            {
                "title": seed.title,
                "summary": seed.interesting,
                "source": seed.source,
                "source_reason": seed.connection,
                "question": seed.question,
            }
        )

    return merged[:max_items]


# ── Auth helpers ───────────────────────────────────────────────────────────────


def _resolve_credentials() -> object | None:
    """ADC → gcloud token の順で認証情報を解決する.

    Cloud Run 環境では ADC が自動的に設定されているため ADC が使用される。
    ローカル開発環境では gcloud の access token を fallback として試みる。

    Returns:
        google.auth.credentials.Credentials オブジェクト、または None。
        None の場合は genai.Client のデフォルト認証機構に委ねる。
    """
    # 1st: Application Default Credentials (Cloud Run / `gcloud auth application-default login`)
    try:
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        logger.debug("news_researcher: using Application Default Credentials")
        return credentials
    except (DefaultCredentialsError, OSError, ValueError):
        logger.debug("news_researcher: ADC not available, trying gcloud token")

    # 2nd: gcloud access token (ローカル開発用 fallback)
    gcloud_bin = shutil.which("gcloud")
    if not gcloud_bin:
        logger.debug("news_researcher: gcloud executable not found")
        return None

    try:
        token = subprocess.run(  # noqa: S603 - 実行コマンドは固定の gcloud バイナリのみ
            [gcloud_bin, "auth", "print-access-token"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout.strip()
        if token:
            logger.debug("news_researcher: using gcloud access token")
            return google_oauth2_credentials.Credentials(token=token)
    except (FileNotFoundError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        logger.debug("news_researcher: gcloud token not available")

    # どちらも使えない場合は None → genai.Client のデフォルトに委ねる
    return None
