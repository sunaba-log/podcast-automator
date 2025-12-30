import datetime  # noqa: D100
import logging
import uuid

import feedparser
import pytz
from feedgen.feed import FeedGenerator

logger = logging.getLogger(__name__)


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
        self.total_episodes = 0
        if self.rss_xml is None:
            logger.warning("No existing RSS XML provided;")
            logger.warning("Execute generate_podcast_rss to create a new feed before updating.")
        else:
            self._parse_rss()

    def _parse_rss(self) -> None:
        """既存のRSS XMLをパースしてFeedGeneratorを初期化."""
        if not self.rss_xml:
            raise ValueError("RSS XML is not set")

        self.fg = FeedGenerator()
        self.fg.load_extension("podcast")

        # feedparserを使用してRSSをパース
        try:
            feed = feedparser.parse(self.rss_xml)

            if feed.bozo and isinstance(feed.bozo_exception, Exception):
                msg = f"Failed to parse RSS: {feed.bozo_exception}"
                raise ValueError(msg)

            # チャンネル(feed)情報を抽出  # noqa: RUF003
            feed_info = feed.feed
            self.fg.title(feed_info.get("title", "sunabalog"))
            self.fg.description(feed_info.get("summary", feed_info.get("subtitle", "30 Days to Build (or Not)")))
            self.fg.language(feed_info.get("language", "ja"))

            # リンク情報を抽出
            for link in feed_info.get("links", []):
                if link.get("rel") == "alternate":
                    self.fg.link(href=link.get("href", "https://sunabalog.com"), rel="alternate")
                    break
            if not self.fg.link():
                self.fg.link(href="https://sunabalog.com", rel="alternate")

            # 著作権情報
            if "rights" in feed_info:
                self.fg.copyright(feed_info["rights"])
            elif "author" in feed_info:
                self.fg.copyright(feed_info["author"])

            # iTunes著作者
            if "author" in feed_info:
                self.fg.author(name=feed_info["author"])

            # iTunes所有者情報
            author_detail = feed_info.get("author_detail", {})
            if "name" in author_detail:
                email = author_detail.get("email", "noreply@example.com")
                self.fg.podcast.itunes_owner(name=author_detail["name"], email=email)

            # iTunes画像
            if "image" in feed_info and "href" in feed_info["image"]:
                self.fg.podcast.itunes_image(feed_info["image"]["href"])

            # iTunes明示的表示
            self.fg.podcast.itunes_explicit("no")

            # iTunes カテゴリ
            if "tags" in feed_info and len(feed_info["tags"]) > 0:
                # 最初のタグをカテゴリとして使用
                category = feed_info["tags"][0].get("term", "Technology")
                self.fg.podcast.itunes_category(category)
            else:
                self.fg.podcast.itunes_category("Technology")

            # iTunes タイプ
            self.fg.podcast.itunes_type("episodic")

            # エピソード(entries)を処理
            for entry in feed.entries:
                item_title = entry.get("title", "Untitled")
                item_description = entry.get("summary", entry.get("description", ""))
                item_guid = entry.get("id", entry.get("link", ""))
                item_link = entry.get("link", "")
                item_creator = entry.get("author", "")
                item_pubdate = None

                # 公開日を抽出
                if "published_parsed" in entry:
                    item_pubdate = datetime.datetime(*entry["published_parsed"][:6], tzinfo=pytz.UTC)

                # エンクロージャ(音声ファイル)を抽出  # noqa: RUF003
                audio_url = ""
                file_size = "0"
                mime_type = "audio/mpeg"
                for link in entry.get("links", []):
                    if link.get("rel") == "enclosure":
                        audio_url = link.get("href", "")
                        file_size = link.get("length", "0")
                        mime_type = link.get("type", "audio/mpeg")
                        break

                # iTunes再生時間
                item_duration = None
                if "itunes_duration" in entry:
                    item_duration = entry["itunes_duration"]

                # iTunes エピソードタイプ
                item_episode_type = entry.get("itunes_episodetype", "full")

                # エピソードデータを構築
                if audio_url:
                    episode_data = {
                        "title": item_title,
                        "description": item_description,
                        "audio_url": audio_url,
                        "guid": item_guid,
                        "mime_type": mime_type,
                        "file_size": int(file_size) if str(file_size).isdigit() else 0,
                    }
                    if item_link:
                        episode_data["link"] = item_link
                    if item_creator:
                        episode_data["creator"] = item_creator
                    if item_duration:
                        episode_data["duration"] = str(item_duration)
                    if item_episode_type:
                        episode_data["episode_type"] = item_episode_type
                    if item_pubdate:
                        episode_data["pub_date"] = item_pubdate

                    # エピソードを追加
                    self.add_episode(episode_data)

        except Exception as e:
            msg = f"Failed to parse RSS XML: {e}"
            raise ValueError(msg) from e

    def _ensure_fg_loaded(self) -> None:
        """FeedGeneratorが読み込まれていることを確認."""
        if self.fg is None:
            raise RuntimeError("RSS feed not loaded. Initialize with rss_xml or call generate_podcast_rss first.")

    def get_total_episodes(self) -> int:
        """RSSフィード内のエピソード数を取得."""
        return self.total_episodes

    def get_latest_episode(self) -> dict | None:
        """最新のエピソード情報を取得.

        Returns:
            最新エピソードの情報を含む辞書、またはエピソードが存在しない場合は None.
        """
        self._ensure_fg_loaded()
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
        self._ensure_fg_loaded()
        self.fg.title(new_title)
        self.rss_xml = self.fg.rss_str(pretty=True).decode("utf-8")

    def update_description(self, new_description: str) -> None:
        """RSS XMLの説明を更新.

        Args:
            new_description: 新しい説明.
        """
        self._ensure_fg_loaded()
        self.fg.description(new_description)
        self.rss_xml = self.fg.rss_str(pretty=True).decode("utf-8")

    def update_category(self, new_category: str) -> None:
        """RSS XMLのカテゴリを更新.

        Args:
            new_category: 新しいカテゴリ (例: "Technology", "Business" など).
        """
        self._ensure_fg_loaded()
        # 既存のカテゴリを削除して新しいものを設定
        self.fg.podcast.itunes_category(new_category)
        self.rss_xml = self.fg.rss_str(pretty=True).decode("utf-8")

    def add_episode(self, episode_data: dict) -> None:
        """新しいエピソードをRSSフィードに追加.

        Args:
            episode_data: エピソード情報を含む辞書. 以下のキーをサポート:
                - title (str): エピソードタイトル(必須)
                - description (str): エピソード説明(必須)
                - link (str): エピソードのリンク
                - audio_url (str): 音声ファイルのURL(必須)
                - duration (str): 再生時間(例: "01:23:45")
                - pub_date (datetime): 公開日時
                - guid (str): ユニークなID(デフォルト: UUID4)
                - creator (str): エピソード作成者
                - file_size (int): 音声ファイルサイズ(バイト)
                - mime_type (str): MIME タイプ(デフォルト: audio/mpeg)
        """
        self._ensure_fg_loaded()

        # 必須フィールドのチェック
        required_fields = ["title", "description", "audio_url"]
        for field in required_fields:
            if field not in episode_data:
                msg = f"Missing required field: {field}"
                raise ValueError(msg)

        # 新しいエントリを作成
        fe = self.fg.add_entry()

        fe.id(episode_data.get("guid", str(uuid.uuid4())))
        fe.title(episode_data["title"])
        fe.description(episode_data["description"])

        # リンクを設定
        if "link" in episode_data:
            fe.link(href=episode_data["link"], rel="alternate")

        # 作成者を設定
        if "creator" in episode_data:
            fe.author(name=episode_data["creator"])

        # 音声ファイルをエンクロージャーとして設定
        mime_type = episode_data.get("mime_type", "audio/mpeg")
        file_size = episode_data.get("file_size", "0")
        fe.enclosure(
            url=episode_data["audio_url"],
            type=mime_type,
            length=str(file_size),
        )

        # 公開日時を設定(デフォルトは現在時刻)
        pub_date = episode_data.get("pub_date", datetime.datetime.now(pytz.UTC))
        fe.pubDate(pub_date)

        # 再生時間を設定(iTunes拡張機能)
        if "duration" in episode_data:
            fe.podcast.itunes_duration(episode_data["duration"])

        # エピソードタイプを設定(iTunes拡張機能)
        episode_type = episode_data.get("episode_type", "full")
        fe.podcast.itunes_episode_type(episode_type)

        self.rss_xml = self.fg.rss_str(pretty=True).decode("utf-8")
        self.total_episodes += 1

    def update_episode(self, episode_id: str, updated_data: dict) -> None:
        """既存のエピソードを更新.

        Args:
            episode_id: 更新するエピソードのID (guid).
            updated_data: 更新する情報を含む辞書. サポートするキー:
                - title (str): タイトル
                - description (str): 説明
                - audio_url (str): 音声ファイルのURL
                - duration (str): 再生時間
                - pub_date (datetime): 公開日時
                - creator (str): エピソード作成者
                - file_size (int): 音声ファイルサイズ
        """
        self._ensure_fg_loaded()

        # チャンネル情報を保存
        old_title = self.fg.title()
        old_description = self.fg.description()
        old_language = self.fg.language()

        # 現在のXMLをfeedparserで再パース
        feed = feedparser.parse(self.rss_xml)

        # RSS XMLからチャンネルリンク情報を抽出
        channel_link = "https://sunabalog.com"
        if feed.feed.get("links"):
            for link in feed.feed["links"]:
                if link.get("rel") == "alternate":
                    channel_link = link.get("href", "https://sunabalog.com")
                    break

        # 指定IDのエピソードを探して更新
        entry_found = False
        for i, entry in enumerate(feed.entries):
            entry_guid = entry.get("id", entry.get("link", ""))
            if entry_guid == episode_id:
                entry_found = True

                # FeedGeneratorをリセット
                self.fg = FeedGenerator()
                self.fg.load_extension("podcast")

                # チャンネル情報を復元
                self.fg.title(old_title)
                self.fg.description(old_description)
                self.fg.language(old_language)
                self.fg.link(href=channel_link, rel="alternate")

                # すべてのエントリを再度追加(更新対象以外)
                self.total_episodes = 0
                for j, entry_item in enumerate(feed.entries):
                    episode_data = {
                        "title": entry_item.get("title", "Untitled"),
                        "description": entry_item.get("summary", entry_item.get("description", "")),
                        "audio_url": "",
                        "guid": entry_item.get("id", entry_item.get("link", "")),
                    }

                    # エンクロージャを抽出
                    for link in entry_item.get("links", []):
                        if link.get("rel") == "enclosure":
                            episode_data["audio_url"] = link.get("href", "")
                            episode_data["mime_type"] = link.get("type", "audio/mpeg")
                            episode_data["file_size"] = (
                                int(link.get("length", "0")) if link.get("length", "0").isdigit() else 0
                            )
                            break

                    if not episode_data["audio_url"]:
                        continue

                    # 更新対象のエピソードはupdated_dataで上書き
                    if j == i:
                        if "title" in updated_data:
                            episode_data["title"] = updated_data["title"]
                        if "description" in updated_data:
                            episode_data["description"] = updated_data["description"]
                        if "audio_url" in updated_data:
                            episode_data["audio_url"] = updated_data["audio_url"]
                        if "file_size" in updated_data:
                            episode_data["file_size"] = updated_data["file_size"]
                        if "mime_type" in updated_data:
                            episode_data["mime_type"] = updated_data["mime_type"]
                        if "duration" in updated_data:
                            episode_data["duration"] = updated_data["duration"]
                        if "creator" in updated_data:
                            episode_data["creator"] = updated_data["creator"]

                    # その他のメタデータを抽出
                    if entry_item.get("author"):
                        episode_data["creator"] = entry_item["author"]
                    if "itunes_duration" in entry_item:
                        episode_data["duration"] = str(entry_item["itunes_duration"])
                    if "published_parsed" in entry_item:
                        episode_data["pub_date"] = datetime.datetime(
                            *entry_item["published_parsed"][:6], tzinfo=pytz.UTC
                        )
                    if entry_item.get("link"):
                        episode_data["link"] = entry_item["link"]

                    self.add_episode(episode_data)

                break

        if not entry_found:
            msg = f"Episode with ID '{episode_id}' not found"
            raise ValueError(msg)

        self.rss_xml = self.fg.rss_str(pretty=True).decode("utf-8")

    def delete_episode(self, episode_id: str) -> None:
        """指定されたエピソードをRSSフィードから削除.

        Args:
            episode_id: 削除するエピソードのID (guid).
        """
        self._ensure_fg_loaded()

        # チャンネル情報を保存
        old_title = self.fg.title()
        old_description = self.fg.description()
        old_language = self.fg.language()

        # 現在のXMLをfeedparserで再パース
        feed = feedparser.parse(self.rss_xml)

        # RSS XMLからチャンネルリンク情報を抽出
        channel_link = "https://sunabalog.com"
        if feed.feed.get("links"):
            for link in feed.feed["links"]:
                if link.get("rel") == "alternate":
                    channel_link = link.get("href", "https://sunabalog.com")
                    break

        # 指定IDのエピソードを探す
        entry_found = False
        entry_index = -1
        for i, entry in enumerate(feed.entries):
            entry_guid = entry.get("id", entry.get("link", ""))
            if entry_guid == episode_id:
                entry_found = True
                entry_index = i
                break

        if not entry_found:
            msg = f"Episode with ID '{episode_id}' not found"
            raise ValueError(msg)

        # FeedGeneratorをリセット
        self.fg = FeedGenerator()
        self.fg.load_extension("podcast")

        # チャンネル情報を復元
        self.fg.title(old_title)
        self.fg.description(old_description)
        self.fg.language(old_language)
        self.fg.link(href=channel_link, rel="alternate")

        # 削除対象以外のエントリを再度追加
        self.total_episodes = 0
        for i, entry in enumerate(feed.entries):
            if i == entry_index:
                # 削除対象なのでスキップ
                continue

            episode_data = {
                "title": entry.get("title", "Untitled"),
                "description": entry.get("summary", entry.get("description", "")),
                "audio_url": "",
                "guid": entry.get("id", entry.get("link", "")),
            }

            # エンクロージャを抽出
            for link in entry.get("links", []):
                if link.get("rel") == "enclosure":
                    episode_data["audio_url"] = link.get("href", "")
                    episode_data["mime_type"] = link.get("type", "audio/mpeg")
                    episode_data["file_size"] = int(link.get("length", "0")) if link.get("length", "0").isdigit() else 0
                    break

            if not episode_data["audio_url"]:
                continue

            # その他のメタデータを抽出
            if entry.get("author"):
                episode_data["creator"] = entry["author"]
            if "itunes_duration" in entry:
                episode_data["duration"] = str(entry["itunes_duration"])
            if "published_parsed" in entry:
                episode_data["pub_date"] = datetime.datetime(*entry["published_parsed"][:6], tzinfo=pytz.UTC)
            if entry.get("link"):
                episode_data["link"] = entry["link"]

            self.add_episode(episode_data)

        self.rss_xml = self.fg.rss_str(pretty=True).decode("utf-8")
        self.total_episodes -= 1
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
        podcast_type: str = "episodic",
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
            podcast_type: ポッドキャストタイプ(デフォルト: "episodic")

        Returns:
            RSS XMLを文字列で返す.
        """
        # 1. FeedGeneratorの初期化
        self.fg = FeedGenerator()

        # Podcast拡張機能(iTunesタグなど)を読み込む  # noqa: RUF003
        self.fg.load_extension("podcast")

        # --- Channel(番組全体)の設定 ---  # noqa: RUF003
        self.fg.title(title)  # 番組タイトル
        self.fg.link(href="https://sunabalog.com", rel="alternate")  # 番組サイト
        self.fg.description(description)  # 番組説明
        self.fg.language(language)

        # 著作者と著作権を設定
        if author != "":
            self.fg.author(name=author)
        if copyright_text:
            self.fg.copyright(copyright_text)

        # ポッドキャスト固有設定
        self.fg.podcast.itunes_category(category)  # カテゴリ(Appleの規定リスト参照)
        self.fg.podcast.itunes_explicit("no")  # explicit指定 (yes/no)
        self.fg.podcast.itunes_image(cover_url)  # 必須: 1400~3000px
        self.fg.podcast.itunes_type(podcast_type)  # ポッドキャストタイプ

        # オーナー情報を設定
        if owner_email != "":
            self.fg.podcast.itunes_owner(name=owner_name, email=owner_email)
        else:
            # emailがない場合はダミーメールアドレスを使用
            self.fg.podcast.itunes_owner(name=owner_name, email="noreply@example.com")

        # --- RSS生成 ---
        # 文字列として取得(Cloudflare R2やS3にアップロードする場合など)  # noqa: RUF003
        rss_str = self.fg.rss_str(pretty=True)
        self.rss_xml = rss_str.decode("utf-8")
        return self.rss_xml

    def get_rss_xml(self) -> str:
        """現在のRSS XMLを取得.

        Returns:
            RSS XML文字列.
        """
        if self.rss_xml is None:
            raise ValueError("RSS XML has not been generated or set")
        return self.rss_xml
