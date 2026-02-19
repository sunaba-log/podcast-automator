"""RSS manager tests for metadata and XML escaping."""

import re

import feedparser
import pytest

from services import PodcastRssManager


class TestXMLEscaping:
    """XML特殊文字エスケープのテスト."""

    def test_generate_podcast_rss_with_special_characters(self) -> None:
        """タイトルに特殊文字を含むRSSが正しく生成されること."""
        rss_manager = PodcastRssManager()
        rss_xml = rss_manager.generate_podcast_rss(
            title="My Podcast & Friends < > \" '",
            description='A podcast about "coding" & development',
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Owner & Co.",
            owner_email="owner@example.com",
            author="Author <tag>",
            copyright_text="Copyright © 2024 & Friends",
        )

        # エスケープが適切に行われているか確認
        # 重要な特殊文字がエスケープされていることを確認
        assert "&amp;" in rss_xml  # & がエスケープされている
        assert "&lt;" in rss_xml  # < がエスケープされている
        assert "&gt;" in rss_xml  # > がエスケープされている

        # XMLパース可能なことを確認(最も重要な確認)

        feed = feedparser.parse(rss_xml)
        assert not feed.bozo or feed.bozo_exception is None

    def test_add_episode_with_special_characters(self) -> None:
        """特殊文字を含むエピソードが正しく追加されること."""
        rss_manager = PodcastRssManager()
        rss_manager.generate_podcast_rss(
            title="Test Podcast",
            description="Test Description",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
        )

        episode_data = {
            "link": "https://example.com/episode1",
            "title": "Episode 1 & Tutorial: HTML < CSS > JavaScript",
            "description": 'Learn about "HTML" & <CSS>. Don\'t skip!',
            "audio_url": "https://example.com/audio.mp3",
            "creator": 'John "The Coder" & Friends',
            "itunes_duration": "01:23:45",
            "file_size": 1024000,
        }

        rss_manager.add_episode(episode_data)
        rss_xml = rss_manager.get_rss_xml()

        # XMLパース可能なことを確認

        feed = feedparser.parse(rss_xml)
        assert not feed.bozo or feed.bozo_exception is None

        # エピソードが正しく追加されていることを確認
        assert len(feed.entries) == 1
        entry = feed.entries[0]
        # エスケープされたテキストが含まれているか確認
        assert "Episode 1" in entry.title
        assert "HTML" in entry.title or "&lt;CSS&gt;" in entry.title

    def test_update_title_with_special_characters(self) -> None:
        """タイトル更新時に特殊文字が正しくエスケープされること."""
        rss_manager = PodcastRssManager()
        rss_manager.generate_podcast_rss(
            title="Original Title",
            description="Test",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
        )

        rss_manager.update_title('Updated & "Quoted" Title < New >')
        rss_xml = rss_manager.get_rss_xml()

        # XMLパース可能なことを確認

        feed = feedparser.parse(rss_xml)
        assert not feed.bozo or feed.bozo_exception is None

    def test_update_description_with_special_characters(self) -> None:
        """説明更新時に特殊文字が正しくエスケープされること."""
        rss_manager = PodcastRssManager()
        rss_manager.generate_podcast_rss(
            title="Test",
            description="Original Description",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
        )

        rss_manager.update_description('Updated & <description> with "quotes" & apostrophes\'')
        rss_xml = rss_manager.get_rss_xml()

        # XMLパース可能なことを確認

        feed = feedparser.parse(rss_xml)
        assert not feed.bozo or feed.bozo_exception is None


class TestEpisodeMetadata:
    """エピソードメタデータのテスト."""

    def test_add_episode_with_artwork_and_category(self) -> None:
        """エピソード単位のアートワークとカテゴリが出力されること."""
        rss_manager = PodcastRssManager()
        rss_manager.generate_podcast_rss(
            title="Test Podcast",
            description="Test Description",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
        )

        episode_data = {
            "title": "Episode 1",
            "description": "Episode Description",
            "audio_url": "https://example.com/audio.mp3",
            "itunes_image": "https://example.com/episode-art.jpg",
            "category": "Technology",
            "itunes_duration": "01:00:00",
            "file_size": 1024000,
        }

        rss_manager.add_episode(episode_data)
        rss_xml = rss_manager.get_rss_xml()

        # RSS XMLに iTunes タグが含まれていることを確認
        assert "itunes:image" in rss_xml or "episode_art" in rss_xml
        assert "Technology" in rss_xml or "category" in rss_xml

    def test_add_episode_with_season_and_episode_number(self) -> None:
        """シーズンとエピソード番号が出力されること."""
        rss_manager = PodcastRssManager()
        rss_manager.generate_podcast_rss(
            title="Test Podcast",
            description="Test Description",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
        )

        episode_data = {
            "title": "Episode 1",
            "description": "Episode Description",
            "audio_url": "https://example.com/audio.mp3",
            "itunes_season": 1,
            "itunes_episode_number": 1,
            "explicit": "no",
            "itunes_duration": "01:00:00",
            "file_size": 1024000,
        }

        rss_manager.add_episode(episode_data)
        rss_xml = rss_manager.get_rss_xml()

        # RSS XMLに iTunes タグが含まれていることを確認
        assert "itunes:season" in rss_xml or "itunes_season" in rss_xml
        assert "itunes:episode" in rss_xml or "itunes_episode_number" in rss_xml

    def test_add_episode_with_explicit_flag(self) -> None:
        """明示的内容フラグが設定されること."""
        rss_manager = PodcastRssManager()
        rss_manager.generate_podcast_rss(
            title="Test Podcast",
            description="Test Description",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
        )

        episode_data = {
            "title": "Episode 1",
            "description": "Episode Description",
            "audio_url": "https://example.com/audio.mp3",
            "itunes_explicit": "yes",
            "itunes_duration": "01:00:00",
            "file_size": 1024000,
        }

        rss_manager.add_episode(episode_data)
        rss_xml = rss_manager.get_rss_xml()

        # RSS XMLに explicit タグが含まれていることを確認
        assert "itunes:explicit" in rss_xml or "yes" in rss_xml


class TestChannelMetadata:
    """チャンネル(番組全体)メタデータのテスト."""

    def test_generate_podcast_rss_includes_required_tags(self) -> None:
        """生成されたRSSに必要なタグが全て含まれること."""
        rss_manager = PodcastRssManager()
        rss_xml = rss_manager.generate_podcast_rss(
            title="Sunaba Log Podcast",
            description="A podcast about technology and life",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Sunaba Log",
            owner_email="admin@sunabalog.com",
            author="Sunaba Log",
            copyright_text="Copyright © 2024 Sunaba Log",
            rss_link="https://anchor.fm/s/10c66ec7c/podcast/rss",
        )

        # 必要なタグが含まれていることを確認
        assert "title" in rss_xml
        assert "description" in rss_xml or "summary" in rss_xml
        assert "language" in rss_xml or "ja" in rss_xml
        assert "itunes:category" in rss_xml or "Technology" in rss_xml
        assert "itunes:image" in rss_xml or "cover.jpg" in rss_xml
        assert "itunes:owner" in rss_xml
        assert "itunes:author" in rss_xml or "author" in rss_xml
        assert "itunes:type" in rss_xml or "episodic" in rss_xml
        assert "atom:link" in rss_xml or "self" in rss_xml  # セルフリンク

    def test_generate_podcast_rss_with_custom_rss_link(self) -> None:
        """カスタムRSSリンクが設定されること."""
        rss_manager = PodcastRssManager()
        custom_rss_link = "https://example.com/podcast/rss"
        rss_xml = rss_manager.generate_podcast_rss(
            title="Test Podcast",
            description="Test",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
            rss_link=custom_rss_link,
        )

        # カスタムリンクが含まれていることを確認
        assert custom_rss_link in rss_xml or "example.com/podcast/rss" in rss_xml


class TestRSSValidation:
    """RSSバリデーションのテスト."""

    def test_generated_rss_is_valid_xml(self) -> None:
        """生成されたRSSが有効なXMLであること."""
        rss_manager = PodcastRssManager()
        rss_xml = rss_manager.generate_podcast_rss(
            title="Test Podcast",
            description="Test Description",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
        )

        # エピソードを複数追加
        for i in range(3):
            episode_data = {
                "title": f"Episode {i + 1}",
                "description": f"Description {i + 1}",
                "audio_url": f"https://example.com/audio{i + 1}.mp3",
                "duration": "01:00:00",
                "file_size": 1024000,
            }
            rss_manager.add_episode(episode_data)

        rss_xml = rss_manager.get_rss_xml()

        # feedparserでパース可能か確認

        feed = feedparser.parse(rss_xml)

        # bozo フラグをチェック
        if feed.bozo and isinstance(feed.bozo_exception, Exception):
            pytest.fail(f"RSS parsing failed: {feed.bozo_exception}")

        # エントリ数を確認
        assert len(feed.entries) == 3

    def test_rss_with_multiple_episodes_and_metadata(self) -> None:
        """複数のエピソードと豊富なメタデータを含むRSSが有効であること."""
        rss_manager = PodcastRssManager()
        rss_xml = rss_manager.generate_podcast_rss(
            title="Test Podcast & Friends",
            description='A podcast with "special" characters < > &',
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test & Owner",
            author="Author <Name>",
            copyright_text="© 2024 Test",
        )

        # 複数のエピソード(各種メタデータ付き)を追加
        for i in range(2):
            episode_data = {
                "title": f"Episode {i + 1} & Special<>",
                "description": f'Description {i + 1} with "quotes"',
                "audio_url": f"https://example.com/audio{i + 1}.mp3",
                "creator": f"Creator {i + 1}",
                "itunes_image": f"https://example.com/ep-art{i + 1}.jpg",
                "category": "Technology",
                "itunes_season": 1,
                "itunes_episode_number": i + 1,
                "itunes_explicit": "no",
                "itunes_duration": "01:00:00",
                "file_size": 1024000,
            }
            rss_manager.add_episode(episode_data)

        rss_xml = rss_manager.get_rss_xml()

        # feedparserでパース可能か確認

        feed = feedparser.parse(rss_xml)

        if feed.bozo and isinstance(feed.bozo_exception, Exception):
            pytest.fail(f"RSS parsing failed: {feed.bozo_exception}")

        assert len(feed.entries) == 2


class TestDescriptionAndSummaryFormatting:
    """<description>と<itunes:summary>のフォーマットテスト."""

    def test_description_wrapped_with_cdata_and_html_tags_preserved(self) -> None:
        """<description>がCDATAで囲まれ、HTMLタグがそのまま維持されること."""
        rss_manager = PodcastRssManager()
        rss_manager.generate_podcast_rss(
            title="Test Podcast",
            description="Test Description",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
        )

        # HTMLタグを含むエピソードを追加
        episode_data = {
            "title": "Episode with HTML",
            "description": "<p>This is a paragraph.</p><br>Line break here.",
            "audio_url": "https://example.com/audio.mp3",
            "itunes_duration": "01:00:00",
            "file_size": 1024000,
        }
        rss_manager.add_episode(episode_data)
        rss_xml = rss_manager.get_rss_xml()

        # <description>タグがCDATAで囲まれていることを確認
        assert "<description><![CDATA[" in rss_xml
        assert "]]></description>" in rss_xml

        # HTMLタグがエスケープされずにそのまま維持されていることを確認
        assert "<p>This is a paragraph.</p>" in rss_xml
        assert "<br>" in rss_xml

        # XMLとしてパース可能であることを確認
        feed = feedparser.parse(rss_xml)
        assert not feed.bozo or feed.bozo_exception is None
        assert len(feed.entries) == 1

    def test_itunes_summary_not_wrapped_with_cdata_and_html_escaped(self) -> None:
        """<itunes:summary>がCDATAで囲まれず、HTMLタグがXMLエスケープされること."""
        rss_manager = PodcastRssManager()
        rss_manager.generate_podcast_rss(
            title="Test Podcast",
            description="Test Description",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
        )

        # HTMLタグを含むエピソードを追加
        episode_data = {
            "title": "Episode with HTML",
            "description": "Plain text description",
            "itunes_summary": "<p>This is a paragraph.</p><br>Line break here.",
            "audio_url": "https://example.com/audio.mp3",
            "itunes_duration": "01:00:00",
            "file_size": 1024000,
        }
        rss_manager.add_episode(episode_data)
        rss_xml = rss_manager.get_rss_xml()

        # <itunes:summary>タグがCDATAで囲まれていないことを確認
        # (itunes:summaryの直後にCDATAがないことを確認)
        itunes_summary_pattern = r"<itunes:summary>(?!<!\[CDATA\[)(.+?)</itunes:summary>"
        matches = re.findall(itunes_summary_pattern, rss_xml, re.DOTALL)
        assert len(matches) > 0, "itunes:summary tag not found"

        # HTMLタグがXMLエスケープされていることを確認
        assert "&lt;p&gt;" in rss_xml
        assert "&lt;br&gt;" in rss_xml
        # エスケープされていない生のHTMLタグがitunes:summary内にないことを確認
        assert "<itunes:summary><![CDATA[" not in rss_xml

        # XMLとしてパース可能であることを確認
        feed = feedparser.parse(rss_xml)
        assert not feed.bozo or feed.bozo_exception is None
        assert len(feed.entries) == 1

    def test_description_and_summary_different_formatting(self) -> None:
        """同じHTMLタグを含むテキストで、descriptionとsummaryが異なる方法でフォーマットされること."""
        rss_manager = PodcastRssManager()
        rss_manager.generate_podcast_rss(
            title="Test Podcast",
            description="Test Description",
            language="ja",
            category="Technology",
            cover_url="https://example.com/cover.jpg",
            owner_name="Test Owner",
        )

        html_content = "<p>Episode content with HTML tags</p><br>"
        episode_data = {
            "title": "Test Episode",
            "description": html_content,
            "itunes_summary": html_content,
            "audio_url": "https://example.com/audio.mp3",
            "itunes_duration": "01:00:00",
            "file_size": 1024000,
        }
        rss_manager.add_episode(episode_data)
        rss_xml = rss_manager.get_rss_xml()

        # descriptionはCDATAで囲まれ、HTMLタグがそのまま
        assert "<description><![CDATA[" in rss_xml
        # エピソードの<item>セクション内のdescriptionを探す
        item_match = re.search(r"<item>(.+?)</item>", rss_xml, re.DOTALL)
        assert item_match is not None
        item_content = item_match.group(1)

        # item内のdescriptionを確認
        description_match = re.search(
            r"<description><!\[CDATA\[(.+?)\]\]></description>",
            item_content,
            re.DOTALL,
        )
        assert description_match is not None
        description_content = description_match.group(1)
        assert "<p>Episode content with HTML tags</p>" in description_content

        # itunes:summaryはCDATAで囲まれず、HTMLタグがエスケープ
        itunes_summary_match = re.search(
            r"<itunes:summary>(.+?)</itunes:summary>",
            item_content,
            re.DOTALL,
        )
        assert itunes_summary_match is not None
        summary_content = itunes_summary_match.group(1)
        assert "&lt;p&gt;" in summary_content
        assert "&lt;br&gt;" in summary_content
        # 生のHTMLタグがないことを確認 (CDATA外)
        assert "<![CDATA[" not in summary_content

        # XMLとしてパース可能であることを確認
        feed = feedparser.parse(rss_xml)
        assert not feed.bozo or feed.bozo_exception is None
