import datetime  # noqa: D100
import logging
import re
import uuid
from typing import Required, TypedDict, Unpack

import feedparser
import pytz
from feedgen.feed import FeedGenerator
from feedparser.util import FeedParserDict

logger = logging.getLogger(__name__)


# podcast basic info keys:
class ChannelData(TypedDict, total=False):
    """ポッドキャストの基本情報の型定義.

    Args:
        title: ポッドキャストタイトル(必須)
        link: ポッドキャストのリンク(必須)
        description: ポッドキャスト説明(必須)
        copyright: 著作権情報
        docs: ドキュメントリンク
        language: 言語コード(例: "ja")
        atom_link: RSSフィードのリンク(必須)
        itunes_author: iTunes著作者
        itunes_category: iTunesカテゴリ
        itunes_image: iTunesカバー画像URL
        itunes_explicit: iTunes明示的表示("yes" or "no")
        itunes_owner_name: iTunesオーナー名
        itunes_owner_email: iTunesオーナーメールアドレス
        itunes_summary: iTunesサマリー
        itunes_type: iTunesタイプ(例: "episodic" or "serial")
    """

    title: Required[str]
    description: Required[str]
    link: str
    copyright: str
    docs: str
    language: str
    atom_link: str
    itunes_author: str
    itunes_category: str
    itunes_image: str
    itunes_explicit: str
    itunes_owner_name: str
    itunes_owner_email: str
    itunes_summary: str
    itunes_type: str


class EpisodeData(TypedDict, total=False):
    """エピソードデータの型定義.

    Args:
        guid: ユニークなID(デフォルト: UUID4)
        title: エピソードタイトル(必須)
        description: エピソード説明(必須)
        audio_url: 音声ファイルのURL(必須)
        file_size: 音声ファイルサイズ(バイト)(必須)
        mime_type: MIME タイプ(デフォルト: audio/mpeg)
        itunes_duration: 再生時間(例: "01:23:45")(必須)
        link: エピソードのリンク
        creator: エピソード作成者
        pub_date: 公開日時
        itunes_summary: iTunesサマリー
        itunes_explicit: iTunes明示的表示("yes" or "no")
        itunes_image: iTunesエピソード画像URL
        itunes_season: iTunesシーズン番号
        itunes_episode_number: iTunesエピソード番号
        itunes_episode_type: iTunesエピソードタイプ(例: "full", "trailer", "bonus")
    """

    guid: Required[str]
    title: Required[str]
    description: Required[str]
    audio_url: Required[str]
    file_size: Required[int]
    mime_type: Required[str]
    itunes_duration: Required[str]
    link: str
    creator: str
    pub_date: datetime.datetime
    itunes_summary: str
    itunes_explicit: str
    itunes_image: str
    itunes_season: int
    itunes_episode_number: int
    itunes_episode_type: str


class PodcastRssManager:
    """ポッドキャストRSS管理クラス."""

    def __init__(self, rss_xml: str | None = None) -> None:
        """ポッドキャストRSS管理クラス.

        Args:
            rss_xml: 既存のRSS XML文字列. 指定しない場合は None.

        Methods:
            add_episode(episode_data): 新しいエピソードを追加.
            update_episode(episode_id, updated_data): 既存のエピソードを更新.
            delete_episode(episode_id): エピソードを削除.
            get_total_episodes(): エピソード数を取得.
            get_latest_episode(): 最新エピソード情報を取得.
            update_title(new_title): タイトルを更新.
            update_description(new_description): 説明を更新.
            update_category(new_category): カテゴリを更新.
            generate_podcast_rss(...): 新しいポッドキャストRSSを生成.
        """
        self.rss_xml = rss_xml if rss_xml is not None else None
        self.fg = None
        self._initialize_fg()

        self.total_episodes = 0
        self.podcast_basic_info = {}  # ポッドキャストの基本情報を格納
        self.episodes: list[EpisodeData] = []

        if self.rss_xml is None:
            logger.warning("No existing RSS XML provided;")
            logger.warning("Execute generate_podcast_rss to create a new feed before updating.")
        else:
            self._parse_rss()
            self._register_channel()
            self._register_episodes()

    def _initialize_fg(self) -> None:
        """FeedGeneratorを初期化."""
        self.fg = FeedGenerator()
        self.fg.load_extension("podcast")
        self.fg.load_extension("dc")

    def _set_podcast_basic_info(self, **kwargs: Unpack[ChannelData]) -> None:
        """ポッドキャストの基本情報を更新."""
        # kwargsで渡された情報を辞書に格納/更新
        for key, value in kwargs.items():
            self.podcast_basic_info[key] = value

    def _register_episode(self, episode: EpisodeData) -> None:
        """エピソード(episode)をFeedGeneratorに登録."""
        # 必須フィールドのチェック
        required_fields = ["title", "description", "audio_url"]
        for field in required_fields:
            if field not in episode:
                msg = f"Missing required field: {field}"
                raise ValueError(msg)

        # 新しいエントリを作成
        fe = self.fg.add_entry()

        # テキストフィールドにエスケープ処理を適用
        fe.id(episode.get("guid", str(uuid.uuid4())))
        fe.title(episode.get("title"))
        fe.description(episode.get("description"))

        # リンクを設定
        if "link" in episode:
            fe.link(href=episode["link"], rel="alternate")

        # 作成者を設定
        if "creator" in episode:
            fe.author(name=episode["creator"])
            fe.dc.dc_creator(episode["creator"])

        # 音声ファイルをエンクロージャーとして設定
        mime_type = episode.get("mime_type", "audio/mpeg")
        file_size = episode.get("file_size", "0")
        fe.enclosure(
            url=episode["audio_url"],
            type=mime_type,
            length=str(file_size),
        )

        # 公開日時を設定(デフォルトは現在時刻)
        pub_date = episode.get("pub_date", datetime.datetime.now(pytz.UTC))
        fe.pubDate(pub_date)

        # 再生時間を設定(iTunes拡張機能)
        if "itunes_duration" in episode and re.match(r"^\d{1,2}:\d{2}:\d{2}$", episode["itunes_duration"]):
            fe.podcast.itunes_duration(episode["itunes_duration"])

        # エピソードタイプを設定(iTunes拡張機能)
        episode_type = episode.get("itunes_episode_type", "full")
        fe.podcast.itunes_episode_type(episode_type)

        # エピソード単位のアートワークを設定
        if "itunes_image" in episode:
            fe.podcast.itunes_image(episode["itunes_image"])

        # シーズンとエピソード番号を設定
        if "itunes_season" in episode:
            fe.podcast.itunes_season(episode["itunes_season"])

        if "itunes_episode_number" in episode:
            fe.podcast.itunes_episode(episode["itunes_episode_number"])

        # 明示的内容フラグを設定
        explicit = episode.get("itunes_explicit", "no")
        fe.podcast.itunes_explicit(explicit)

        # サマリーを設定(descriptionと同じでよい)
        if "itunes_summary" not in episode:
            fe.podcast.itunes_summary(episode.get("description"))
        else:
            fe.podcast.itunes_summary(episode.get("itunes_summary"))

    def _register_episodes(self) -> None:
        self.total_episodes = 0
        # エピソード(episodes)を処理
        logger.info("### Registering episodes...")
        logger.info("%d episodes to register.", len(self.episodes))
        for episode in self.episodes:
            self._register_episode(episode)
            self.total_episodes += 1

    def _register_channel(self) -> None:
        """内部データからRSS XMLを生成."""
        # --- Channel(番組全体)の設定 ---
        self.fg.title(self.podcast_basic_info.get("title", "sunabalog"))
        self.fg.description(self.podcast_basic_info.get("description", "30 Days to Build (or Not)"))
        self.fg.language(self.podcast_basic_info.get("language", "ja"))

        # atom:linkの設定
        show_link = self.podcast_basic_info.get("link", "")
        if show_link != "":
            # 番組サイト
            self.fg.link(href=show_link, rel="alternate")
            # ウェブサイトのHTML版へのリンク(alternate)
            self.fg.link(href=show_link, rel="alternate", type="text/html")
        # rss_linkが指定されていればatom:linkも設定
        rss_link = self.podcast_basic_info.get("atom_link", "")
        if rss_link != "":
            # フィードの一意なID
            self.fg.id(rss_link)
            # Atomフィード自体へのリンク(self)
            self.fg.link(href=rss_link, rel="self", type="application/atom+xml")
            self.fg.atom_file("atom.xml")

        # オーナー情報を設定
        if "itunes_owner_name" in self.podcast_basic_info:
            self.fg.podcast.itunes_owner(
                name=self.podcast_basic_info["itunes_owner_name"],
                email=self.podcast_basic_info.get("itunes_owner_email", "noreply@example.com"),
            )
        # 著作者と著作権を設定
        if "copyright" in self.podcast_basic_info:
            self.fg.copyright(self.podcast_basic_info["copyright"])
        if "itunes_author" in self.podcast_basic_info:
            self.fg.author(name=self.podcast_basic_info["itunes_author"])
            self.fg.podcast.itunes_author(self.podcast_basic_info["itunes_author"])

        # ポッドキャスト固有設定
        if "itunes_summary" in self.podcast_basic_info:
            self.fg.podcast.itunes_summary(self.podcast_basic_info["itunes_summary"])
        if "itunes_image" in self.podcast_basic_info:
            self.fg.podcast.itunes_image(self.podcast_basic_info["itunes_image"])
        if "itunes_category" in self.podcast_basic_info:
            self.fg.podcast.itunes_category(self.podcast_basic_info["itunes_category"])
        self.fg.podcast.itunes_explicit(self.podcast_basic_info.get("itunes_explicit", "no"))
        self.fg.podcast.itunes_type(self.podcast_basic_info.get("itunes_type", "episodic"))

        logger.info("### Channel information registered.")

    def _parse_rss(self) -> None:
        """既存のRSS XMLをパースしてFeedGeneratorを初期化."""
        if not self.rss_xml:
            raise ValueError("RSS XML is not set")

        # feedparserを使用してRSSをパース
        logger.info("### Parsing existing RSS XML...")
        try:
            feed = feedparser.parse(self.rss_xml)
            if feed.bozo and isinstance(feed.bozo_exception, Exception):
                msg = f"Failed to parse RSS: {feed.bozo_exception}"
                raise ValueError(msg)

            # チャンネル(feed)メタデータを抽出
            logger.info("### Extracting channel data...")
            self._extract_channel_data(feed)

            # エピソード(entries)を処理
            logger.info("### Extracting episode data...")
            self.episodes = [self._extract_episode_data(entry) for entry in feed.entries]

        except Exception as e:
            msg = f"Failed to parse RSS XML: {e}"
            raise ValueError(msg) from e

    def _wrap_elements_with_cdata(self, xml_str: str, tags: list[str]) -> str:
        """指定されたタグの内容をCDATAセクションで囲みます.

        Args:
            xml_str: RSS XML文字列
            tags: CDATA で囲むタグ名のリスト(例:['title', 'description'])
                  XML の名前空間付きタグにも対応(例:'itunes:summary')

        Returns:
            CDATA で囲まれた XML 文字列
        """
        for tag in tags:
            # <tag>内容</tag> または <ns:tag>内容</ns:tag> に対応
            # タグ内容をキャプチャ
            pattern = f"<{re.escape(tag)}>(.+?)</{re.escape(tag)}>"

            def replace_func(match: re.Match, tag: str = tag) -> str:
                content = match.group(1)
                # 既に CDATA で囲まれていないか確認
                if "<![CDATA[" in content:
                    return match.group(0)
                # 内容をエスケープせずに CDATA で囲む
                return f"<{tag}><![CDATA[{content}]]></{tag}>"

            xml_str = re.sub(pattern, replace_func, xml_str, flags=re.DOTALL)

        return xml_str

    def _extract_channel_data(self, feed: dict) -> dict:
        """チャンネル(feed)の全メタデータを抽出しま.

        Args:
            feed: feedparser でパースされた feed オブジェクト

        Returns:
            チャンネルメタデータを含む辞書
        """
        # チャンネル(feed)情報を抽出  # noqa: RUF003
        feed_info = feed.feed
        logger.info("### RSS parsed successfully.")
        # どんなチャンネル情報があるかログ出力
        logger.info("Feed info keys: %s", list(feed.keys()))
        logger.info("Feed info: %s", list(feed_info))
        self._set_podcast_basic_info(
            title=feed_info.get("title", "sunabalog"),
            description=feed_info.get("summary", feed_info.get("subtitle", "30 Days to Build (or Not)")),
            language=feed_info.get("language", "ja"),
            copyright=feed_info.get("rights", feed_info.get("author", "")),
            atom_link=feed_info.get("id", "https://podcast.sunabalog.com/sunabalog/feed.xml"),
            itunes_author=feed_info.get("author", ""),
            itunes_category=(
                feed_info["tags"][0].get("term", "Technology")
                if "tags" in feed_info and len(feed_info["tags"]) > 0
                else "Technology"
            ),
            itunes_image=(feed_info["image"]["href"] if "image" in feed_info and "href" in feed_info["image"] else ""),
            itunes_explicit="no",
            itunes_owner_name=feed_info.get("author_detail", {}).get("name", ""),
            itunes_owner_email=feed_info.get("author_detail", {}).get("email", ""),
            itunes_summary=feed_info.get("summary", feed_info.get("subtitle", "30 Days to Build (or Not)")),
            itunes_type="episodic",
        )

        # リンク情報を抽出
        for link in feed_info.get("links", []):
            if link.get("rel") == "alternate":
                self._set_podcast_basic_info(link=link.get("href", "https://sunabalog.com"))
                break

    def _extract_episode_data(self, entry: FeedParserDict) -> EpisodeData:
        """エピソード(entry)の全メタデータを抽出します.

        Args:
            entry: feedparser でパースされたエントリ

        Returns:
            エピソードメタデータを含む辞書
        """
        # エピソード情報を抽出
        entry_guid = entry.get("id")
        entry_title = entry.get("title", "Untitled")
        entry_itunes_summary = entry.get("summary", "")
        entry_description = (
            entry.get("content", "")[0].get("value", "") if "content" in entry else entry.get("summary", "")
        )
        entry_link = entry.get("links", "")[0].get("href", "") if "links" in entry and len(entry["links"]) > 0 else ""
        entry_creator = entry.get("author", "")

        # 公開日を抽出
        if "published_parsed" in entry:
            entry_pubdate = datetime.datetime(*entry["published_parsed"][:6], tzinfo=pytz.UTC)
        else:
            entry_pubdate = entry.get("published", None)

        # エンクロージャ(音声ファイル)を抽出  # noqa: RUF003
        entry_audio_url = ""
        entry_file_size = "0"
        entry_mime_type = "audio/mpeg"
        for link in entry.get("links", []):
            if link.get("rel") == "enclosure":
                entry_audio_url = link.get("href", "")
                entry_file_size = link.get("length", "0")
                entry_mime_type = link.get("type", "audio/mpeg")
                break

        # iTunes再生時間
        entry_duration = None
        if "itunes_duration" in entry:
            entry_duration = entry["itunes_duration"]

        # iTunes エピソードタイプ
        entry_episode_type = entry.get("itunes_episodetype", "full")

        # エピソードデータを構築
        if entry_audio_url:
            episode_data: EpisodeData = {
                "guid": entry_guid,
                "title": entry_title,
                "description": entry_description,
                "audio_url": entry_audio_url,
                "file_size": int(entry_file_size) if entry_file_size.isdigit() else 0,
                "mime_type": entry_mime_type,
                "itunes_duration": str(entry_duration),
                "itunes_summary": entry_itunes_summary,
            }
            if entry_link:
                episode_data["link"] = entry_link
            if entry_creator:
                episode_data["creator"] = entry_creator
            if entry_pubdate:
                episode_data["pub_date"] = entry_pubdate
            if entry_episode_type:
                episode_data["itunes_episodetype"] = entry_episode_type

        return episode_data

    def get_total_episodes(self) -> int:
        """RSSフィード内のエピソード数を取得."""
        return self.total_episodes

    def get_latest_episode(self) -> dict | None:
        """最新のエピソード情報を取得.

        Returns:
            最新エピソードの情報を含む辞書、またはエピソードが存在しない場合は None.
        """
        if not self.fg.entrys:
            return None

        latest_entry = self.fg.entrys[-1]
        episode_info = {
            "title": latest_entry.title(),
            "description": latest_entry.description(),
            "guid": latest_entry.id(),
            "link": latest_entry.link(),
        }

        # エンクロージャ情報
        enclosures = latest_entry.enclosures()
        if enclosures:
            enclosure = enclosures[0]
            episode_info.update(
                {
                    "audio_url": enclosure["url"],
                    "mime_type": enclosure.get("type", "audio/mpeg"),
                    "file_size": int(enclosure.get("length", "0"))
                    if str(enclosure.get("length", "0")).isdigit()
                    else 0,
                }
            )

        return episode_info

    def update_title(self, new_title: str) -> None:
        """RSS XMLのタイトルを更新.

        Args:
            new_title: 新しいタイトル.
        """
        self.fg.title(new_title)
        rss_str = self.fg.rss_str(pretty=True).decode("utf-8")
        # タイトルを CDATA で囲む
        rss_str = self._wrap_elements_with_cdata(rss_str, ["title"])
        self.rss_xml = rss_str

    def update_description(self, new_description: str) -> None:
        """RSS XMLの説明を更新.

        Args:
            new_description: 新しい説明.
        """
        self.fg.description(new_description)
        rss_str = self.fg.rss_str(pretty=True).decode("utf-8")
        # 説明と iTunes サマリーを CDATA で囲む
        rss_str = self._wrap_elements_with_cdata(rss_str, ["description", "itunes:summary"])
        self.rss_xml = rss_str

    def update_category(self, new_category: str) -> None:
        """RSS XMLのカテゴリを更新.

        Args:
            new_category: 新しいカテゴリ (例: "Technology", "Business" など).
        """
        # 既存のカテゴリを削除して新しいものを設定
        self.fg.podcast.itunes_category(new_category)
        rss_str = self.fg.rss_str(pretty=True).decode("utf-8")
        # 必要に応じて CDATA を適用
        rss_str = self._wrap_elements_with_cdata(rss_str, ["itunes:category"])
        self.rss_xml = rss_str

    def add_episode(self, episode_data: EpisodeData) -> None:
        """新しいエピソードをRSSフィードに追加.

        Args:
            episode_data: エピソード情報を含む辞書. 以下のキーをサポート:
                - title (str): エピソードタイトル(必須)
                - description (str): エピソード説明(必須)
                - link (str): エピソードのリンク
                - guid (str): ユニークなID(デフォルト: UUID4)
                - creator (str): エピソード作成者
                - pub_date (datetime): 公開日時
                - audio_url (str): 音声ファイルのURL(必須)
                - file_size (int): 音声ファイルサイズ(バイト)
                - mime_type (str): MIME タイプ(デフォルト: audio/mpeg)
                - itunes_summary: iTunesサマリー
                - itunes_explicit: iTunes明示的表示("yes" or "no")
                - itunes_duration: iTunes再生時間(例: "01:23:45")
                - itunes_image: iTunesエピソード画像URL
                - itunes_season: iTunesシーズン番号
                - itunes_episode_number: iTunesエピソード番号
                - itunes_episode_type: iTunesエピソードタイプ(例: "full", "trailer", "bonus")

        """
        self._register_episode(episode_data)
        self.episodes.append(episode_data)
        self.total_episodes += 1

        self.set_rss_xml()

    def update_episode(self, episode_id: str, updated_data: EpisodeData) -> None:
        """既存のエピソードを更新.

        Args:
            episode_id: 更新するエピソードのID (guid).
            updated_data: 更新する情報を含む辞書. サポートするキー:
                - title (str): タイトル
                - description (str): 説明
                - audio_url (str): 音声ファイルのURL
                - itunes_duration (str): 再生時間
                - pub_date (datetime): 公開日時
                - creator (str): エピソード作成者
                - file_size (int): 音声ファイルサイズ
        """
        # 指定IDのエピソードを探して更新
        episode_found = False
        target_index = -1
        for i, episode in enumerate(self.episodes):
            episode_guid = episode.get("guid")
            if episode_guid == episode_id:
                episode_found = True
                target_index = i
        if not episode_found:
            msg = f"Episode with ID '{episode_id}' not found"
            raise ValueError(msg)

        # すべてのエントリを再度追加(更新対象以外は完全に継承)
        self._initialize_fg()
        self._register_channel()

        self.total_episodes = 0
        for j, episode in enumerate(self.episodes):
            # 更新対象のエピソードはupdated_dataで上書き
            if j == target_index:
                # updated_dataで指定されたフィールドを上書き
                for key, value in updated_data.items():
                    episode[key] = value
            self._register_episode(episode)
            self.total_episodes += 1

        self.set_rss_xml()

    def delete_episode(self, episode_id: str) -> None:
        """指定されたエピソードをRSSフィードから削除.

        Args:
            episode_id: 削除するエピソードのID (guid).
        """
        # 指定IDのエピソードを探す
        episode_found = False
        episode_index = -1
        for i, episode in enumerate(self.episodes):
            episode_guid = episode.get("guid")
            if episode_guid == episode_id:
                episode_found = True
                episode_index = i

        if not episode_found:
            msg = f"Episode with ID '{episode_id}' not found"
            raise ValueError(msg)

        self.episodes.pop(episode_index)

        # すべてのエントリを再度追加(更新対象以外は完全に継承)
        self._initialize_fg()
        self._register_channel()

        # 削除対象以外のエントリを再度追加
        self._register_episodes()
        self.set_rss_xml()
        logger.info("%d エピソード数を更新済み in delete_episode", self.total_episodes)

    def generate_podcast_rss(
        self,
        title: str,
        description: str,
        language: str,
        category: str,
        cover_url: str,
        owner_name: str,
        owner_email: str = "",
        author: str = "",
        copyright_text: str = "",
        show_link: str = "",
        podcast_type: str = "episodic",
        rss_link: str = "https://anchor.fm/s/10c66ec7c/podcast/rss",
    ) -> str:
        """新しいポッドキャストRSSフィードを生成.

        Args:
            title: ポッドキャストタイトル
            description: ポッドキャスト説明
            language: 言語コード (例: "ja")
            category: ポッドキャストカテゴリ
            cover_url: カバーアート画像のURL
            owner_name: オーナー名
            owner_email: オーナーメール (オプション)
            author: ポッドキャスト著作者 (オプション)
            copyright_text: 著作権表記 (オプション)
            show_link: ポッドキャストのウェブサイトリンク (オプション)
            podcast_type: ポッドキャストタイプ(デフォルト: "episodic")
            rss_link: RSS フィードのセルフリンク (オプション)

        Returns:
            RSS XMLを文字列で返す.
        """
        # 1. FeedGeneratorの初期化
        self.fg = FeedGenerator()

        # Podcast拡張機能(iTunesタグなど)を読み込む  # noqa: RUF003
        self.fg.load_extension("podcast")
        self.fg.load_extension("dc")  # Dublin Core拡張機能(作成者タグなど)

        # --- Channel(番組全体)の設定 ---  # noqa: RUF003
        self.fg.title(title)  # 番組タイトル
        if show_link != "":
            self.fg.link(href=show_link, rel="alternate")  # 番組サイト
            # ウェブサイトのHTML版へのリンク(alternate)
            self.fg.link(href=show_link, rel="alternate", type="text/html")
        # rss_linkが指定されていればatom:linkも設定
        if rss_link != "":
            self.fg.id(rss_link)  # フィードの一意なID
            # Atomフィード自体へのリンク(self)
            self.fg.link(href=rss_link, rel="self", type="application/atom+xml")
            # フィードをファイルに出力
            # self.fg.atom_file("atom.xml")

        self.fg.link(href=rss_link, rel="self", type="application/rss+xml")  # セルフリンク
        self.fg.description(description)  # 番組説明
        self.fg.language(language)

        # 著作者と著作権を設定
        if author != "":
            self.fg.author(name=author)
            self.fg.podcast.itunes_author(author)
        if copyright_text:
            self.fg.copyright(copyright_text)

        # ポッドキャスト固有設定
        self.fg.podcast.itunes_category(category)  # カテゴリ(Appleの規定リスト参照)
        self.fg.podcast.itunes_explicit("no")  # explicit指定 (yes/no)
        self.fg.podcast.itunes_image(cover_url)  # 必須: 1400~3000px
        self.fg.podcast.itunes_type(podcast_type)  # ポッドキャストタイプ
        self.fg.podcast.itunes_summary(description)  # iTunes概要

        # オーナー情報を設定
        if owner_email != "":
            self.fg.podcast.itunes_owner(name=owner_name, email=owner_email)
        else:
            # emailがない場合はダミーメールアドレスを使用
            self.fg.podcast.itunes_owner(name=owner_name, email="noreply@example.com")

        # --- RSS生成 ---
        # 文字列として取得(Cloudflare R2やS3にアップロードする場合など)  # noqa: RUF003
        self.set_rss_xml()
        return self.rss_xml

    def get_rss_xml(self) -> str:
        """現在のRSS XMLを取得.

        Returns:
            RSS XML文字列.
        """
        if self.rss_xml is None:
            raise ValueError("RSS XML has not been generated or set")
        return self.rss_xml

    def set_rss_xml(self) -> None:
        """現在のRSS XMLを取得.

        Returns:
            RSS XML文字列.
        """
        # RSS生成後にCDATAを適用
        rss_str = self.fg.rss_str(pretty=True).decode("utf-8")
        cdata_tags = ["title", "description", "itunes:summary", "dc:creator", "itunes:author", "copyright"]
        rss_str = self._wrap_elements_with_cdata(rss_str, cdata_tags)
        self.rss_xml = rss_str
